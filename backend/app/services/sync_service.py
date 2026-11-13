import unicodedata
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy.orm import Session

from app.connectors.classroom_client import ClassroomClient
from app.connectors.cotemig_client import CotemigClient
from app.models.academic import CotemigGradeSnapshot, CourseMapping, StudentMap, SyncHistory
from app.models.coursework import Activity, Submission, Theme
from app.services.calc_engine import calculate_course_gradebook


def _normalize_name(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name or "")
    ascii_str = "".join(c for c in nfkd if not unicodedata.combining(c))
    return " ".join(ascii_str.lower().strip().split())


def _parse_classroom_due_date(work: dict[str, Any]) -> datetime | None:
    due = work.get("dueDate")
    if not due:
        return None
    year = due.get("year", 2026)
    month = due.get("month", 1)
    day = due.get("day", 1)
    due_time = work.get("dueTime") or {}
    hour = due_time.get("hours", 23)
    minute = due_time.get("minutes", 59)
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


class SyncService:
    def __init__(self) -> None:
        self.classroom = ClassroomClient()
        self.cotemig = CotemigClient()

    def list_external_sources(self) -> dict[str, Any]:
        classroom_courses: list[dict[str, Any]] = []
        if self.classroom.get_status()["connected"]:
            try:
                classroom_courses = self.classroom.fetch_courses()
            except Exception:
                classroom_courses = []

        cotemig_classes = self.cotemig.fetch_classes()
        return {
            "classroom_courses": classroom_courses,
            "cotemig_classes": cotemig_classes,
        }

    def sync_course(self, db: Session, course_map_id: int) -> dict[str, Any]:
        course = db.get(CourseMapping, course_map_id)
        if not course:
            raise ValueError(f"Turma {course_map_id} não encontrada.")

        now = datetime.now(timezone.utc)
        classroom_students: list[dict[str, Any]] = []
        cotemig_students: list[dict[str, Any]] = []

        # 1. Google Classroom (se conectado e mapeado)
        if course.classroom_course_id and self.classroom.get_status()["connected"]:
            topics = self.classroom.fetch_topics(course.classroom_course_id)
            topic_map: dict[str, Theme] = {}
            for idx, tp in enumerate(topics):
                tid = tp.get("topicId")
                existing = (
                    db.query(Theme)
                    .filter(
                        Theme.course_map_id == course.id,
                        Theme.classroom_topic_id == tid,
                    )
                    .first()
                )
                if not existing:
                    existing = Theme(
                        course_map_id=course.id,
                        classroom_topic_id=tid,
                        title=tp.get("name", f"Tema {idx + 1}"),
                        order_index=idx,
                    )
                    db.add(existing)
                    db.flush()
                else:
                    existing.title = tp.get("name", existing.title)
                topic_map[tid] = existing

            classroom_students = self.classroom.fetch_students(course.classroom_course_id)
            works = self.classroom.fetch_coursework(course.classroom_course_id)
            work_objs: list[Activity] = []

            for w in works:
                wid = w.get("id")
                act = (
                    db.query(Activity)
                    .filter(
                        Activity.course_map_id == course.id,
                        Activity.classroom_work_id == wid,
                    )
                    .first()
                )
                topic_id = w.get("topicId")
                theme_id = topic_map[topic_id].id if topic_id in topic_map else None
                max_pts = float(w.get("maxPoints") or 100.0)
                if not act:
                    act = Activity(
                        course_map_id=course.id,
                        theme_id=theme_id,
                        classroom_work_id=wid,
                        title=w.get("title", "Atividade"),
                        due_date=_parse_classroom_due_date(w),
                        classroom_max_points=max_pts,
                        custom_points_weight=min(max_pts, 10.0),
                        work_type=w.get("workType", "ASSIGNMENT"),
                    )
                    db.add(act)
                    db.flush()
                else:
                    act.title = w.get("title", act.title)
                    act.classroom_max_points = max_pts
                    if theme_id and act.theme_id is None:
                        act.theme_id = theme_id
                work_objs.append(act)

        # 2. Portal Cotemig (se mapeado)
        if course.cotemig_class_id:
            cotemig_students = self.cotemig.fetch_students(course.cotemig_class_id)
            grades = self.cotemig.fetch_grades(course.cotemig_class_id)
            db.query(CotemigGradeSnapshot).filter(
                CotemigGradeSnapshot.course_map_id == course.id
            ).delete()
            for g in grades:
                db.add(
                    CotemigGradeSnapshot(
                        course_map_id=course.id,
                        cotemig_ra=g["ra"],
                        student_name=g["student_name"],
                        stage_name=g.get("stage_name", "Etapa 1"),
                        official_grade=float(g["official_grade"]),
                        captured_at=now,
                    )
                )

        # 3. Conciliação De/Para de Alunos (E-mail -> RA -> Similaridade de Nome)
        if classroom_students or cotemig_students:
            self._reconcile_students(db, course.id, classroom_students, cotemig_students)

        # 4. Submissions do Classroom (se conectado)
        if course.classroom_course_id and self.classroom.get_status()["connected"]:
            student_by_cid = {
                s.classroom_user_id: s
                for s in db.query(StudentMap).filter(StudentMap.course_map_id == course.id).all()
                if s.classroom_user_id
            }
            for act in db.query(Activity).filter(Activity.course_map_id == course.id).all():
                subs = self.classroom.fetch_submissions(
                    course.classroom_course_id, act.classroom_work_id
                )
                for sub_data in subs:
                    uid = sub_data.get("userId")
                    st = student_by_cid.get(uid)
                    if not st:
                        continue
                    sub = (
                        db.query(Submission)
                        .filter(
                            Submission.activity_id == act.id,
                            Submission.student_map_id == st.id,
                        )
                        .first()
                    )
                    assignment_sub = sub_data.get("assignmentSubmission") or {}
                    has_att = bool(assignment_sub.get("attachments")) or sub_data.get("state") in (
                        "NEW",
                        "CREATED",
                    )
                    if not sub:
                        sub = Submission(activity_id=act.id, student_map_id=st.id)
                        db.add(sub)
                    sub.state = sub_data.get("state", "NEW")
                    sub.is_late = bool(sub_data.get("late", False))
                    sub.has_attachments = has_att
                    sub.assigned_grade = sub_data.get("assignedGrade")
                    sub.draft_grade = sub_data.get("draftGrade")
                    sub.updated_at = now

        course.last_sync_at = now
        db.add(
            SyncHistory(
                course_map_id=course.id,
                source="all",
                status="success",
                details=f"Sincronização concluída ({len(classroom_students)} Classroom / {len(cotemig_students)} Cotemig).",
                synced_at=now,
            )
        )
        db.commit()

        # 5. Dispara motor de cálculo
        gradebook = calculate_course_gradebook(db, course.id, persist=True)
        return {
            "status": "success",
            "course_id": course.id,
            "synced_at": now.isoformat(),
            "students_count": len(gradebook["students"]),
        }

    def _reconcile_students(
        self,
        db: Session,
        course_map_id: int,
        classroom_students: list[dict[str, Any]],
        cotemig_students: list[dict[str, Any]],
    ) -> None:
        existing_students = (
            db.query(StudentMap).filter(StudentMap.course_map_id == course_map_id).all()
        )
        by_cid = {s.classroom_user_id: s for s in existing_students if s.classroom_user_id}
        by_ra = {s.cotemig_ra: s for s in existing_students if s.cotemig_ra}

        matched_cotemig_ras: set[str] = set()

        for cs in classroom_students:
            uid = cs.get("userId")
            profile = cs.get("profile") or {}
            full_name = (profile.get("name") or {}).get("fullName", "Aluno Classroom")
            email = (profile.get("emailAddress") or "").lower().strip()

            cot_match = None
            method = "unmatched"
            for cot in cotemig_students:
                if cot.get("email") and email and cot["email"].lower().strip() == email:
                    cot_match = cot
                    method = "email"
                    break
            if not cot_match:
                norm_c = _normalize_name(full_name)
                best_ratio = 0.0
                for cot in cotemig_students:
                    if cot["ra"] in matched_cotemig_ras:
                        continue
                    ratio = SequenceMatcher(None, norm_c, _normalize_name(cot["full_name"])).ratio()
                    if ratio >= 0.85 and ratio > best_ratio:
                        best_ratio = ratio
                        cot_match = cot
                        method = "name"

            student = by_cid.get(uid)
            if not student and cot_match:
                student = by_ra.get(cot_match["ra"])
            if not student:
                student = StudentMap(course_map_id=course_map_id, full_name=full_name)
                db.add(student)

            student.classroom_user_id = uid
            student.full_name = full_name
            student.email = email or student.email
            if cot_match:
                student.cotemig_ra = cot_match["ra"]
                student.status_cotemig = cot_match.get("status", "ATIVO")
                student.match_method = method
                matched_cotemig_ras.add(cot_match["ra"])
            elif not student.cotemig_ra:
                student.status_cotemig = "ORFAO_CLASSROOM"
                student.match_method = "unmatched"

        for cot in cotemig_students:
            if cot["ra"] in matched_cotemig_ras:
                continue
            student = by_ra.get(cot["ra"])
            if not student:
                student = StudentMap(
                    course_map_id=course_map_id,
                    cotemig_ra=cot["ra"],
                    full_name=cot["full_name"],
                    email=cot.get("email"),
                    status_cotemig="ORFAO_COTEMIG" if classroom_students else cot.get("status", "ATIVO"),
                    match_method="ra" if not classroom_students else "unmatched",
                )
                db.add(student)


def seed_demo_data(db: Session) -> dict[str, Any]:
    """Popula o banco local SQLite com dados realistas de 2 turmas para validação imediata."""
    existing = db.query(CourseMapping).count()
    if existing > 0:
        courses = db.query(CourseMapping).all()
        for c in courses:
            calculate_course_gradebook(db, c.id, persist=True)
        return {"status": "already_seeded", "courses_count": existing}

    now = datetime.now(timezone.utc)

    # Turma 1: Programação Orientada a Objetos - 3º Ano A
    c1 = CourseMapping(
        classroom_course_id="GC-POO-3A-2026",
        cotemig_class_id="COT-3A-POO-2026",
        name="Programação Orientada a Objetos - 3º Ano A",
        section="3º Ano A - Técnico em Informática",
        term_period="2026/2",
        min_passing_grade=60.0,
        use_draft_grades=False,
        last_sync_at=now,
    )
    db.add(c1)
    db.flush()

    t1 = Theme(
        course_map_id=c1.id,
        classroom_topic_id="TOP-POO-1",
        title="Tema 1: Fundamentos OO e Encapsulamento",
        max_points_cap=10.0,
        rounding_rule="decimal_1",
        order_index=1,
    )
    t2 = Theme(
        course_map_id=c1.id,
        classroom_topic_id="TOP-POO-2",
        title="Tema 2: Herança, Polimorfismo e Interfaces",
        max_points_cap=10.0,
        rounding_rule="half_point",
        order_index=2,
    )
    t3 = Theme(
        course_map_id=c1.id,
        classroom_topic_id="TOP-POO-3",
        title="Tema 3: Projeto Integrador",
        max_points_cap=10.0,
        rounding_rule="decimal_1",
        order_index=3,
    )
    db.add_all([t1, t2, t3])
    db.flush()

    acts_c1 = [
        Activity(
            course_map_id=c1.id,
            theme_id=t1.id,
            classroom_work_id="CW-101",
            title="Lista 01 - Classes e Objetos",
            due_date=now - timedelta(days=28),
            classroom_max_points=100.0,
            custom_points_weight=4.0,
        ),
        Activity(
            course_map_id=c1.id,
            theme_id=t1.id,
            classroom_work_id="CW-102",
            title="Prática 02 - Construtores e Getters",
            due_date=now - timedelta(days=21),
            classroom_max_points=10.0,
            custom_points_weight=6.0,
        ),
        Activity(
            course_map_id=c1.id,
            theme_id=t2.id,
            classroom_work_id="CW-103",
            title="Lab 03 - Herança e Sobrescrita",
            due_date=now - timedelta(days=14),
            classroom_max_points=100.0,
            custom_points_weight=6.0,
        ),
        Activity(
            course_map_id=c1.id,
            theme_id=t2.id,
            classroom_work_id="CW-104",
            title="Lab 04 - Interfaces e Coleções",
            due_date=now - timedelta(days=7),
            classroom_max_points=100.0,
            custom_points_weight=6.0,  # Soma 12 pts, teto 10 pts!
        ),
        Activity(
            course_map_id=c1.id,
            theme_id=t3.id,
            classroom_work_id="CW-105",
            title="Entrega Parcial - API do Projeto",
            due_date=now - timedelta(days=2),
            classroom_max_points=100.0,
            custom_points_weight=5.0,
        ),
        Activity(
            course_map_id=c1.id,
            theme_id=t3.id,
            classroom_work_id="CW-106",
            title="Apresentação Final do Sistema",
            due_date=now + timedelta(days=7),
            classroom_max_points=100.0,
            custom_points_weight=5.0,
        ),
    ]
    db.add_all(acts_c1)
    db.flush()

    students_c1_data = [
        ("GC-U01", "22300201", "Gabriel Almeida Nunes", "gabriel.nunes@aluno.cotemig.com.br", "ATIVO", "email", 27.0),
        ("GC-U02", "22300202", "Helena Barbosa Dias", "helena.dias@aluno.cotemig.com.br", "ATIVO", "email", 22.0),
        ("GC-U03", "22300203", "Igor Carvalho Mendes", "igor.mendes@aluno.cotemig.com.br", "ATIVO", "email", 14.0),
        ("GC-U04", "22300204", "Juliana Duarte Gomes", "juliana.gomes@aluno.cotemig.com.br", "ATIVO", "email", 25.5),
        ("GC-U05", "22300205", "Lucas Eduardo Silva", "lucas.silva@aluno.cotemig.com.br", "ATIVO", "email", 17.5),
        ("GC-U06", "22300206", "Mariana Ferreira Castro", "mariana.castro@aluno.cotemig.com.br", "ATIVO", "email", 9.0),
        ("GC-U07", "22300207", "Nicolas Pereira Teixeira", "nicolas.teixeira@aluno.cotemig.com.br", "ATIVO", "email", 21.0),
        (None, "22300208", "Rafael Vieira Moreira", "rafael.moreira@aluno.cotemig.com.br", "ORFAO_COTEMIG", "unmatched", None),
        ("GC-U09", None, "Sofia Mendes Oliveira", "sofia.oliveira@gmail.com", "ORFAO_CLASSROOM", "unmatched", None),
    ]

    # Matriz de desempenho simulado para cobrir todos os cenários R01–R18
    profiles = [
        # (notas_ratio_por_atividade, states, lates, has_att, drafts)
        ([0.95, 0.90, 0.92, 0.95, 0.90, None], ["RETURNED", "RETURNED", "RETURNED", "RETURNED", "RETURNED", "TURNED_IN"], [False, False, False, False, False, False], [True]*6, [None]*5 + [88.0]),
        ([0.85, 0.80, 0.78, 0.80, None, None], ["RETURNED", "RETURNED", "RETURNED", "RETURNED", "TURNED_IN", "CREATED"], [False, True, False, False, False, False], [True]*6, [None]*6),
        ([0.45, 0.40, 0.50, 0.35, 0.40, None], ["RETURNED", "RETURNED", "RETURNED", "RETURNED", "RETURNED", "NEW"], [False, False, True, False, False, False], [True, True, True, False, True, True], [None]*6),  # Entregam mas não pontuam (R14)
        ([0.92, 0.88, 0.85, 0.90, None, None], ["RETURNED", "RETURNED", "RETURNED", "RETURNED", "TURNED_IN", "NEW"], [False]*6, [True]*6, [None, None, None, None, 92.0, None]),  # Draft grade (R17) + Pendente correção
        ([0.85, 0.82, None, None, None, None], ["RETURNED", "RETURNED", "NEW", "CREATED", "NEW", "NEW"], [False]*6, [True]*6, [None]*6),  # Boa nota mas não entrega (R15)
        ([0.30, 0.25, None, None, None, None], ["RETURNED", "RETURNED", "NEW", "NEW", "NEW", "NEW"], [True, True, False, False, False, False], [True]*6, [None]*6),  # Lista Vermelha (R13)
        ([0.75, 0.80, 0.70, 0.75, None, None], ["RETURNED", "RETURNED", "RETURNED", "RETURNED", "TURNED_IN", "NEW"], [False, False, True, True, True, False], [True]*6, [None]*6),
        ([None]*6, ["NEW"]*6, [False]*6, [True]*6, [None]*6),  # Órfão Cotemig
        ([0.80, 0.75, 0.85, None, None, None], ["RETURNED", "RETURNED", "RETURNED", "TURNED_IN", "NEW", "NEW"], [False]*6, [True]*6, [None]*6),  # Órfão Classroom
    ]

    for idx, (cid, ra, name, email, status_cot, method, off_grade) in enumerate(students_c1_data):
        st = StudentMap(
            course_map_id=c1.id,
            classroom_user_id=cid,
            cotemig_ra=ra,
            full_name=name,
            email=email,
            status_cotemig=status_cot,
            match_method=method,
        )
        db.add(st)
        db.flush()

        if off_grade is not None and ra:
            db.add(
                CotemigGradeSnapshot(
                    course_map_id=c1.id,
                    student_map_id=st.id,
                    cotemig_ra=ra,
                    student_name=name,
                    stage_name="Etapa 1",
                    official_grade=off_grade,
                    captured_at=now,
                )
            )

        ratios, states, lates, atts, drafts = profiles[idx]
        for a_idx, act in enumerate(acts_c1):
            ratio = ratios[a_idx]
            assigned = round(ratio * act.classroom_max_points, 1) if ratio is not None else None
            sub = Submission(
                activity_id=act.id,
                student_map_id=st.id,
                state=states[a_idx],
                is_late=lates[a_idx],
                has_attachments=atts[a_idx],
                assigned_grade=assigned,
                draft_grade=drafts[a_idx],
                turned_in_at=(act.due_date - timedelta(hours=4)) if states[a_idx] in ("TURNED_IN", "RETURNED") and act.due_date else None,
                updated_at=now - timedelta(days=max(0, 6 - a_idx)),
            )
            db.add(sub)

    # Turma 2: Banco de Dados Relacional - 2º Ano B
    c2 = CourseMapping(
        classroom_course_id="GC-BD-2B-2026",
        cotemig_class_id="COT-2B-BD-2026",
        name="Banco de Dados Relacional - 2º Ano B",
        section="2º Ano B - Técnico em Informática",
        term_period="2026/2",
        min_passing_grade=60.0,
        use_draft_grades=False,
        last_sync_at=now,
    )
    db.add(c2)
    db.flush()

    t2_1 = Theme(
        course_map_id=c2.id,
        classroom_topic_id="TOP-BD-1",
        title="Tema 1: Modelagem MER e Normalização",
        max_points_cap=15.0,
        rounding_rule="decimal_1",
        order_index=1,
    )
    t2_2 = Theme(
        course_map_id=c2.id,
        classroom_topic_id="TOP-BD-2",
        title="Tema 2: SQL DDL, DML e Joins",
        max_points_cap=15.0,
        rounding_rule="decimal_1",
        order_index=2,
    )
    db.add_all([t2_1, t2_2])
    db.flush()

    acts_c2 = [
        Activity(
            course_map_id=c2.id,
            theme_id=t2_1.id,
            classroom_work_id="CW-201",
            title="Diagrama ER - Clínica Médica",
            due_date=now - timedelta(days=18),
            classroom_max_points=100.0,
            custom_points_weight=15.0,
        ),
        Activity(
            course_map_id=c2.id,
            theme_id=t2_2.id,
            classroom_work_id="CW-202",
            title="Consultas SQL Avançadas",
            due_date=now - timedelta(days=5),
            classroom_max_points=100.0,
            custom_points_weight=15.0,
        ),
    ]
    db.add_all(acts_c2)
    db.flush()

    students_c2_data = [
        ("GC-B01", "22400101", "Ana Clara Ribeiro", "ana.ribeiro@aluno.cotemig.com.br", 26.5, [0.90, 0.88]),
        ("GC-B02", "22400102", "Bruno Henrique Costa", "bruno.costa@aluno.cotemig.com.br", 18.0, [0.65, 0.55]),
        ("GC-B03", "22400103", "Camila Ferreira Lima", "camila.lima@aluno.cotemig.com.br", 24.0, [0.82, 0.78]),
        ("GC-B04", "22400104", "Daniel Oliveira Souza", "daniel.souza@aluno.cotemig.com.br", 11.5, [0.40, None]),
        ("GC-B05", "22400105", "Eduarda Martins Alves", "eduarda.alves@aluno.cotemig.com.br", 20.0, [0.70, 0.68]),
    ]

    for cid, ra, name, email, off_grade, ratios in students_c2_data:
        st = StudentMap(
            course_map_id=c2.id,
            classroom_user_id=cid,
            cotemig_ra=ra,
            full_name=name,
            email=email,
            status_cotemig="ATIVO",
            match_method="email",
        )
        db.add(st)
        db.flush()

        db.add(
            CotemigGradeSnapshot(
                course_map_id=c2.id,
                student_map_id=st.id,
                cotemig_ra=ra,
                student_name=name,
                stage_name="Etapa 1",
                official_grade=off_grade,
                captured_at=now,
            )
        )

        for a_idx, act in enumerate(acts_c2):
            r = ratios[a_idx]
            db.add(
                Submission(
                    activity_id=act.id,
                    student_map_id=st.id,
                    state="RETURNED" if r is not None else "TURNED_IN",
                    is_late=(a_idx == 1 and r is None),
                    has_attachments=True,
                    assigned_grade=round(r * 100.0, 1) if r is not None else None,
                    draft_grade=None,
                    updated_at=now - timedelta(days=3),
                )
            )

    db.add(
        SyncHistory(
            course_map_id=c1.id,
            source="demo_seed",
            status="success",
            details="Base inicial de demonstração carregada com 2 turmas (POO 3A e BD 2B).",
            synced_at=now,
        )
    )
    db.commit()

    calculate_course_gradebook(db, c1.id, persist=True)
    calculate_course_gradebook(db, c2.id, persist=True)

    return {"status": "seeded", "courses_count": 2}

