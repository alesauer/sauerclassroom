from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.models.academic import CotemigGradeSnapshot, CourseMapping, StudentMap
from app.models.coursework import Activity, Submission, Theme


def apply_rounding(value: float, rule: str = "decimal_1") -> float:
    """Aplica a regra de arredondamento configurada para o tema (RF08.4)."""
    if rule == "integer":
        return float(round(value))
    if rule == "half_point":
        return round(value * 2.0) / 2.0
    if rule == "decimal_1":
        return round(value, 1)
    return round(value, 2)


def calculate_activity_points(
    obtained_grade: float | None,
    classroom_max_points: float,
    custom_points_weight: float,
) -> float:
    """Calcula a pontuação proporcional da atividade (RF08.3)."""
    if obtained_grade is None or classroom_max_points <= 0 or custom_points_weight <= 0:
        return 0.0
    ratio = obtained_grade / classroom_max_points
    return round(ratio * custom_points_weight, 4)


def calculate_course_gradebook(
    db: Session, course_map_id: int, persist: bool = True
) -> dict[str, Any]:
    """
    Executa o motor de cálculo completo para uma turma (RF08, RF10, RF11).
    Retorna a matriz estruturada de alunos, temas, atividades e indicadores.
    """
    course = db.get(CourseMapping, course_map_id)
    if not course:
        raise ValueError(f"Turma {course_map_id} não encontrada.")

    themes = (
        db.query(Theme)
        .filter(Theme.course_map_id == course_map_id)
        .order_by(Theme.order_index.asc(), Theme.id.asc())
        .all()
    )
    activities = (
        db.query(Activity)
        .filter(Activity.course_map_id == course_map_id)
        .order_by(Activity.due_date.asc().nulls_last(), Activity.id.asc())
        .all()
    )
    students = (
        db.query(StudentMap)
        .filter(StudentMap.course_map_id == course_map_id)
        .order_by(StudentMap.full_name.asc())
        .all()
    )

    activity_ids = [a.id for a in activities]
    submissions = (
        db.query(Submission).filter(Submission.activity_id.in_(activity_ids)).all()
        if activity_ids
        else []
    )
    sub_by_pair: dict[tuple[int, int], Submission] = {
        (s.student_map_id, s.activity_id): s for s in submissions
    }

    snapshots = (
        db.query(CotemigGradeSnapshot)
        .filter(CotemigGradeSnapshot.course_map_id == course_map_id)
        .all()
    )
    official_by_ra = {snap.cotemig_ra: snap.official_grade for snap in snapshots}

    # Agrupa atividades por tema (None -> "Sem Tema")
    activities_by_theme: dict[int | None, list[Activity]] = defaultdict(list)
    for act in activities:
        activities_by_theme[act.theme_id].append(act)

    theme_dicts: list[dict[str, Any]] = []
    total_possible_course = 0.0

    for theme in themes:
        t_acts = [a for a in activities_by_theme.get(theme.id, []) if a.include_in_calc]
        raw_possible = sum(a.custom_points_weight for a in t_acts)
        effective_possible = (
            min(raw_possible, theme.max_points_cap)
            if theme.max_points_cap is not None
            else raw_possible
        )
        total_possible_course += effective_possible
        theme_dicts.append(
            {
                "id": theme.id,
                "title": theme.title,
                "max_points_cap": theme.max_points_cap,
                "rounding_rule": theme.rounding_rule,
                "order_index": theme.order_index,
                "raw_possible": round(raw_possible, 2),
                "effective_possible": round(effective_possible, 2),
            }
        )

    # Atividades sem tema atribuído
    unthemed_acts = [a for a in activities_by_theme.get(None, []) if a.include_in_calc]
    if unthemed_acts:
        raw_unthemed = sum(a.custom_points_weight for a in unthemed_acts)
        total_possible_course += raw_unthemed
        theme_dicts.append(
            {
                "id": None,
                "title": "Sem Tema",
                "max_points_cap": None,
                "rounding_rule": "decimal_1",
                "order_index": 9999,
                "raw_possible": round(raw_unthemed, 2),
                "effective_possible": round(raw_unthemed, 2),
            }
        )

    total_possible_course = round(total_possible_course, 2)
    student_rows: list[dict[str, Any]] = []

    for student in students:
        theme_scores: dict[str, dict[str, Any]] = {}
        activity_cells: dict[str, dict[str, Any]] = {}
        total_points = 0.0
        delivered_count = 0
        pending_count = 0
        late_count = 0
        no_attachment_count = 0

        for td in theme_dicts:
            tid = td["id"]
            t_acts = activities_by_theme.get(tid, [])
            raw_sum = 0.0

            for act in t_acts:
                sub = sub_by_pair.get((student.id, act.id))
                state = sub.state if sub else "NEW"
                is_late = sub.is_late if sub else False
                has_att = sub.has_attachments if sub else True
                assigned = sub.assigned_grade if sub else None
                draft = sub.draft_grade if sub else None

                effective_grade = assigned
                if effective_grade is None and course.use_draft_grades:
                    effective_grade = draft

                calc_pts = (
                    calculate_activity_points(
                        effective_grade, act.classroom_max_points, act.custom_points_weight
                    )
                    if act.include_in_calc
                    else 0.0
                )

                if sub and persist:
                    sub.calculated_points = round(calc_pts, 2)

                if act.include_in_calc:
                    raw_sum += calc_pts
                    if state in ("TURNED_IN", "RETURNED"):
                        delivered_count += 1
                        if not has_att:
                            no_attachment_count += 1
                    else:
                        pending_count += 1
                    if is_late:
                        late_count += 1

                activity_cells[str(act.id)] = {
                    "activity_id": act.id,
                    "state": state,
                    "is_late": is_late,
                    "has_attachments": has_att,
                    "assigned_grade": assigned,
                    "draft_grade": draft,
                    "calculated_points": round(calc_pts, 2),
                    "include_in_calc": act.include_in_calc,
                }

            capped = (
                min(raw_sum, td["max_points_cap"])
                if td["max_points_cap"] is not None
                else raw_sum
            )
            final_theme_pts = apply_rounding(capped, td["rounding_rule"])
            total_points += final_theme_pts

            key = str(tid) if tid is not None else "unthemed"
            theme_scores[key] = {
                "theme_id": tid,
                "title": td["title"],
                "raw_sum": round(raw_sum, 2),
                "final_points": final_theme_pts,
                "possible_points": td["effective_possible"],
            }

        total_points = round(total_points, 2)
        total_included_acts = sum(1 for a in activities if a.include_in_calc)
        submission_rate = (
            round((delivered_count / total_included_acts) * 100.0, 1)
            if total_included_acts > 0
            else 0.0
        )
        percentage = (
            round((total_points / total_possible_course) * 100.0, 1)
            if total_possible_course > 0
            else 0.0
        )

        # Classificação de risco (RF11)
        if percentage >= course.min_passing_grade:
            risk_status = "APROVADO"
        elif percentage >= (course.min_passing_grade * 0.75) and pending_count <= 2:
            risk_status = "ATENCAO"
        else:
            risk_status = "RISCO"

        official_grade = official_by_ra.get(student.cotemig_ra) if student.cotemig_ra else None

        student_rows.append(
            {
                "student_map_id": student.id,
                "full_name": student.full_name,
                "email": student.email,
                "cotemig_ra": student.cotemig_ra,
                "classroom_user_id": student.classroom_user_id,
                "status_cotemig": student.status_cotemig,
                "match_method": student.match_method,
                "theme_scores": theme_scores,
                "activity_cells": activity_cells,
                "total_points": total_points,
                "total_possible": total_possible_course,
                "percentage": percentage,
                "submission_rate": submission_rate,
                "delivered_count": delivered_count,
                "pending_count": pending_count,
                "late_count": late_count,
                "no_attachment_count": no_attachment_count,
                "risk_status": risk_status,
                "cotemig_official_grade": official_grade,
                "grade_divergence": (
                    round(total_points - official_grade, 2)
                    if official_grade is not None
                    else None
                ),
            }
        )

    if persist:
        db.commit()

    return {
        "course": {
            "id": course.id,
            "name": course.name,
            "section": course.section,
            "term_period": course.term_period,
            "classroom_course_id": course.classroom_course_id,
            "cotemig_class_id": course.cotemig_class_id,
            "min_passing_grade": course.min_passing_grade,
            "use_draft_grades": course.use_draft_grades,
            "last_sync_at": course.last_sync_at.isoformat() if course.last_sync_at else None,
            "total_possible_points": total_possible_course,
        },
        "themes": theme_dicts,
        "activities": [
            {
                "id": a.id,
                "theme_id": a.theme_id,
                "title": a.title,
                "classroom_work_id": a.classroom_work_id,
                "due_date": a.due_date.isoformat() if a.due_date else None,
                "classroom_max_points": a.classroom_max_points,
                "custom_points_weight": a.custom_points_weight,
                "include_in_calc": a.include_in_calc,
                "work_type": a.work_type,
            }
            for a in activities
        ],
        "students": student_rows,
    }

