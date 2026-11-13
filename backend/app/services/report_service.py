import csv
import io
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.models.academic import CourseMapping, StudentMap
from app.models.coursework import Activity, Submission
from app.services.calc_engine import calculate_course_gradebook

REPORT_CATALOG: list[dict[str, str]] = [
    {"code": "R01", "category": "Notas e Desempenho", "title": "Boletim Consolidado por Tema (Mapa de Pontos)", "description": "Tabela por turma exibindo os alunos, pontos por tema, soma total e aproveitamento."},
    {"code": "R02", "category": "Notas e Desempenho", "title": "Espelho Detalhado por Atividade", "description": "Matriz completa cruzando Aluno x Atividade com nota original, pontos convertidos e status."},
    {"code": "R03", "category": "Notas e Desempenho", "title": "Ranking e Distribuição de Notas", "description": "Estatísticas da turma (maior, menor, média, mediana, desvio padrão) e histograma de faixas."},
    {"code": "R04", "category": "Notas e Desempenho", "title": "Desempenho Comparativo por Tema", "description": "Comparação da média de aproveitamento da turma em cada tema."},
    {"code": "R05", "category": "Notas e Desempenho", "title": "Simulador de Fechamento", "description": "Projeção de quantos pontos faltam para cada aluno atingir a média mínima do Cotemig."},
    {"code": "R06", "category": "Engajamento e Prazos", "title": "Pendências por Aluno (Lista de Cobrança)", "description": "Lista individualizada das atividades não entregues (NEW / CREATED)."},
    {"code": "R07", "category": "Engajamento e Prazos", "title": "Pontualidade e Atrasos", "description": "Ranking de entregas fora do prazo e taxa de pontualidade por aluno."},
    {"code": "R08", "category": "Engajamento e Prazos", "title": "Taxa de Adesão por Atividade", "description": "Percentual de entregas no prazo, com atraso, pendentes e sem anexo por atividade."},
    {"code": "R09", "category": "Engajamento e Prazos", "title": "Evolução Temporal de Engajamento", "description": "Série temporal semanal de entregas e aproveitamento ao longo do período."},
    {"code": "R10", "category": "Conciliação", "title": "Auditoria de Divergência de Notas", "description": "Compara a soma calculada no sistema com a nota oficial lançada no Portal Cotemig."},
    {"code": "R11", "category": "Conciliação", "title": "Auditoria de Matrículas vs. Sala Virtual", "description": "Aponta alunos órfãos (só no Cotemig ou só no Classroom) e status de conciliação."},
    {"code": "R12", "category": "Conciliação", "title": "Espelho Pronto para Lançamento", "description": "Planilha ordenada por RA/nome na pauta do Portal Cotemig para digitação rápida."},
    {"code": "R13", "category": "Alerta e Risco", "title": "Lista Vermelha (Risco de Reprovação/Evasão)", "description": "Alunos com baixo aproveitamento combinado com alto número de pendências."},
    {"code": "R14", "category": "Alerta e Risco", "title": "Entregam mas Não Pontuam", "description": "Alunos com alta taxa de entrega mas notas baixas, indicando necessidade de reforço."},
    {"code": "R15", "category": "Alerta e Risco", "title": "Boa Nota mas Não Entregam", "description": "Alunos com bom desempenho nas tarefas feitas mas muitas atividades em branco."},
    {"code": "R16", "category": "Operacionais", "title": "Fila de Correção Pendente", "description": "Entregas (TURNED_IN) sem nota atribuída em todas as turmas, ordenadas pelas mais antigas."},
    {"code": "R17", "category": "Operacionais", "title": "Notas em Rascunho (draftGrade)", "description": "Atividades já corrigidas em rascunho no Classroom, mas ainda não devolvidas."},
    {"code": "R18", "category": "Operacionais", "title": "Panorama Geral Multi-Turmas", "description": "Visão executiva consolidando média geral, entregas e pendências de todas as disciplinas."},
]


def _get_meta(code: str) -> dict[str, str]:
    for item in REPORT_CATALOG:
        if item["code"] == code:
            return item
    raise ValueError(f"Relatório '{code}' não encontrado no catálogo (R01–R18).")


def _resolve_course_id(db: Session, course_map_id: int | None) -> int:
    if course_map_id is not None:
        return course_map_id
    first = db.query(CourseMapping).order_by(CourseMapping.id.asc()).first()
    if not first:
        raise ValueError("Nenhuma turma cadastrada no banco. Sincronize ou carregue os dados demo.")
    return first.id


def generate_report(
    db: Session, report_code: str, course_map_id: int | None = None
) -> dict[str, Any]:
    code = report_code.upper()
    meta = _get_meta(code)
    now = datetime.now(timezone.utc)

    # Relatórios multi-turmas (R16, R17, R18)
    if code in ("R16", "R17", "R18"):
        return _generate_global_report(db, code, meta, now, course_map_id)

    cid = _resolve_course_id(db, course_map_id)
    gb = calculate_course_gradebook(db, cid, persist=False)
    course = gb["course"]
    themes = gb["themes"]
    activities = gb["activities"]
    students = gb["students"]

    columns: list[dict[str, str]] = []
    rows: list[dict[str, Any]] = []
    summary: dict[str, Any] = {}
    chart_data: list[dict[str, Any]] = []

    if code == "R01":
        columns = [{"key": "ra", "label": "RA"}, {"key": "student", "label": "Aluno"}]
        for t in themes:
            columns.append({"key": f"theme_{t['id']}", "label": f"{t['title']} (/{t['effective_possible']})"})
        columns.extend([
            {"key": "total", "label": f"Total (/{course['total_possible_points']})"},
            {"key": "percentage", "label": "Aproveitamento (%)"},
            {"key": "status", "label": "Situação"},
        ])
        for s in students:
            row: dict[str, Any] = {
                "ra": s["cotemig_ra"] or "-",
                "student": s["full_name"],
                "total": s["total_points"],
                "percentage": s["percentage"],
                "status": s["risk_status"],
            }
            for t in themes:
                key = str(t["id"]) if t["id"] is not None else "unthemed"
                row[f"theme_{t['id']}"] = s["theme_scores"].get(key, {}).get("final_points", 0.0)
            rows.append(row)
        avg_pct = round(sum(s["percentage"] for s in students) / len(students), 1) if students else 0.0
        summary = {"total_alunos": len(students), "media_aproveitamento": avg_pct}

    elif code == "R02":
        columns = [
            {"key": "ra", "label": "RA"},
            {"key": "student", "label": "Aluno"},
            {"key": "activity", "label": "Atividade"},
            {"key": "state", "label": "Status Entrega"},
            {"key": "assigned", "label": "Nota Classroom"},
            {"key": "converted", "label": "Pontos Convertidos"},
        ]
        for s in students:
            for a in activities:
                cell = s["activity_cells"].get(str(a["id"]), {})
                rows.append({
                    "ra": s["cotemig_ra"] or "-",
                    "student": s["full_name"],
                    "activity": a["title"],
                    "state": cell.get("state", "NEW"),
                    "assigned": cell.get("assigned_grade") if cell.get("assigned_grade") is not None else "-",
                    "converted": cell.get("calculated_points", 0.0),
                })
        summary = {"total_registros": len(rows), "atividades": len(activities)}

    elif code == "R03":
        columns = [
            {"key": "rank", "label": "Posição"},
            {"key": "ra", "label": "RA"},
            {"key": "student", "label": "Aluno"},
            {"key": "total", "label": "Total Pontos"},
            {"key": "percentage", "label": "Aproveitamento (%)"},
            {"key": "band", "label": "Faixa"},
        ]
        sorted_students = sorted(students, key=lambda x: x["total_points"], reverse=True)
        bands = {"0-59%": 0, "60-79%": 0, "80-100%": 0}
        for idx, s in enumerate(sorted_students, start=1):
            pct = s["percentage"]
            band = "80-100%" if pct >= 80 else ("60-79%" if pct >= 60 else "0-59%")
            bands[band] += 1
            rows.append({
                "rank": idx,
                "ra": s["cotemig_ra"] or "-",
                "student": s["full_name"],
                "total": s["total_points"],
                "percentage": pct,
                "band": band,
            })
        scores = [s["total_points"] for s in students]
        summary = {
            "maior_nota": max(scores) if scores else 0.0,
            "menor_nota": min(scores) if scores else 0.0,
            "media": round(statistics.mean(scores), 2) if scores else 0.0,
            "mediana": round(statistics.median(scores), 2) if scores else 0.0,
            "desvio_padrao": round(statistics.pstdev(scores), 2) if len(scores) > 1 else 0.0,
        }
        chart_data = [{"name": k, "quantidade": v} for k, v in bands.items()]

    elif code == "R04":
        columns = [
            {"key": "theme", "label": "Tema / Tópico"},
            {"key": "possible", "label": "Pontos Possíveis"},
            {"key": "avg_points", "label": "Média da Turma"},
            {"key": "avg_pct", "label": "Aproveitamento Médio (%)"},
        ]
        for t in themes:
            key = str(t["id"]) if t["id"] is not None else "unthemed"
            vals = [s["theme_scores"].get(key, {}).get("final_points", 0.0) for s in students]
            avg_p = round(sum(vals) / len(vals), 2) if vals else 0.0
            pct = round((avg_p / t["effective_possible"]) * 100, 1) if t["effective_possible"] > 0 else 0.0
            rows.append({
                "theme": t["title"],
                "possible": t["effective_possible"],
                "avg_points": avg_p,
                "avg_pct": pct,
            })
            chart_data.append({"name": t["title"], "aproveitamento": pct, "media": avg_p})
        summary = {"total_temas": len(themes)}

    elif code == "R05":
        columns = [
            {"key": "ra", "label": "RA"},
            {"key": "student", "label": "Aluno"},
            {"key": "current_points", "label": "Pontos Atuais"},
            {"key": "target_points", "label": "Meta Mínima"},
            {"key": "remaining_possible", "label": "Pontos Ainda em Aberto"},
            {"key": "points_needed", "label": "Pontos Necessários"},
            {"key": "feasibility", "label": "Viabilidade"},
        ]
        total_pos = course["total_possible_points"]
        target_pts = round((course["min_passing_grade"] / 100.0) * total_pos, 2)
        for s in students:
            open_pts = sum(
                a["custom_points_weight"]
                for a in activities
                if a["include_in_calc"]
                and s["activity_cells"].get(str(a["id"]), {}).get("assigned_grade") is None
            )
            needed = max(0.0, round(target_pts - s["total_points"], 2))
            if needed == 0:
                feas = "Meta Atingida"
            elif needed <= open_pts:
                feas = "Alcançável"
            else:
                feas = "Risco Crítico (Insuficiente)"
            rows.append({
                "ra": s["cotemig_ra"] or "-",
                "student": s["full_name"],
                "current_points": s["total_points"],
                "target_points": target_pts,
                "remaining_possible": round(open_pts, 2),
                "points_needed": needed,
                "feasibility": feas,
            })
        summary = {"meta_minima_pct": course["min_passing_grade"], "meta_em_pontos": target_pts}

    elif code == "R06":
        columns = [
            {"key": "ra", "label": "RA"},
            {"key": "student", "label": "Aluno"},
            {"key": "pending_count", "label": "Qtd. Pendências"},
            {"key": "pending_titles", "label": "Atividades Não Entregues"},
        ]
        for s in students:
            pend = [
                a["title"]
                for a in activities
                if a["include_in_calc"]
                and s["activity_cells"].get(str(a["id"]), {}).get("state") in ("NEW", "CREATED")
            ]
            if pend:
                rows.append({
                    "ra": s["cotemig_ra"] or "-",
                    "student": s["full_name"],
                    "pending_count": len(pend),
                    "pending_titles": ", ".join(pend),
                })
        summary = {"alunos_com_pendencias": len(rows)}

    elif code == "R07":
        columns = [
            {"key": "ra", "label": "RA"},
            {"key": "student", "label": "Aluno"},
            {"key": "delivered", "label": "Total Entregas"},
            {"key": "late_count", "label": "Entregas com Atraso"},
            {"key": "punctuality_rate", "label": "Pontualidade (%)"},
        ]
        for s in students:
            deliv = s["delivered_count"]
            late = s["late_count"]
            punct = round(((deliv - late) / deliv) * 100.0, 1) if deliv > 0 else 100.0
            rows.append({
                "ra": s["cotemig_ra"] or "-",
                "student": s["full_name"],
                "delivered": deliv,
                "late_count": late,
                "punctuality_rate": punct,
            })
        rows.sort(key=lambda r: r["late_count"], reverse=True)
        summary = {"total_atrasos": sum(r["late_count"] for r in rows)}

    elif code == "R08":
        columns = [
            {"key": "activity", "label": "Atividade"},
            {"key": "on_time", "label": "No Prazo"},
            {"key": "late", "label": "Com Atraso"},
            {"key": "pending", "label": "Não Entregues"},
            {"key": "no_attachment", "label": "Sem Anexo"},
            {"key": "adhesion_pct", "label": "Adesão (%)"},
        ]
        total_st = len(students) or 1
        for a in activities:
            on_time = late = pend = no_att = 0
            for s in students:
                cell = s["activity_cells"].get(str(a["id"]), {})
                st_state = cell.get("state", "NEW")
                if st_state in ("TURNED_IN", "RETURNED"):
                    if cell.get("is_late"):
                        late += 1
                    else:
                        on_time += 1
                    if not cell.get("has_attachments", True):
                        no_att += 1
                else:
                    pend += 1
            adhesion = round(((on_time + late) / total_st) * 100.0, 1)
            rows.append({
                "activity": a["title"],
                "on_time": on_time,
                "late": late,
                "pending": pend,
                "no_attachment": no_att,
                "adhesion_pct": adhesion,
            })
            chart_data.append({"name": a["title"][:22], "no_prazo": on_time, "atraso": late, "pendente": pend})
        summary = {"total_atividades": len(activities)}

    elif code == "R09":
        columns = [
            {"key": "period", "label": "Semana / Atividade"},
            {"key": "due_date", "label": "Data Limite"},
            {"key": "delivery_rate", "label": "Taxa Entrega (%)"},
            {"key": "avg_score_pct", "label": "Desempenho Médio (%)"},
        ]
        for a in activities:
            delivered = 0
            scores_pct: list[float] = []
            for s in students:
                cell = s["activity_cells"].get(str(a["id"]), {})
                if cell.get("state") in ("TURNED_IN", "RETURNED"):
                    delivered += 1
                if cell.get("assigned_grade") is not None and a["classroom_max_points"] > 0:
                    scores_pct.append((cell["assigned_grade"] / a["classroom_max_points"]) * 100.0)
            deliv_rate = round((delivered / len(students)) * 100.0, 1) if students else 0.0
            avg_sc = round(sum(scores_pct) / len(scores_pct), 1) if scores_pct else 0.0
            due_str = a["due_date"][:10] if a["due_date"] else "Sem prazo"
            rows.append({
                "period": a["title"],
                "due_date": due_str,
                "delivery_rate": deliv_rate,
                "avg_score_pct": avg_sc,
            })
            chart_data.append({"name": due_str, "entrega": deliv_rate, "desempenho": avg_sc})
        summary = {"pontos_temporais": len(rows)}

    elif code == "R10":
        columns = [
            {"key": "ra", "label": "RA"},
            {"key": "student", "label": "Aluno"},
            {"key": "system_grade", "label": "Calculado (Sistema)"},
            {"key": "cotemig_grade", "label": "Portal Cotemig"},
            {"key": "divergence", "label": "Diferença"},
            {"key": "audit_status", "label": "Auditoria"},
        ]
        divergences = 0
        for s in students:
            off = s["cotemig_official_grade"]
            diff = s["grade_divergence"]
            if off is None:
                status = "Sem lançamento no Cotemig"
            elif abs(diff) >= 0.1:
                status = "DIVERGENTE"
                divergences += 1
            else:
                status = "CONCILIADO"
            rows.append({
                "ra": s["cotemig_ra"] or "-",
                "student": s["full_name"],
                "system_grade": s["total_points"],
                "cotemig_grade": off if off is not None else "-",
                "divergence": diff if diff is not None else "-",
                "audit_status": status,
            })
        summary = {"total_divergencias": divergences}

    elif code == "R11":
        columns = [
            {"key": "student", "label": "Aluno"},
            {"key": "email", "label": "E-mail"},
            {"key": "ra", "label": "RA Cotemig"},
            {"key": "classroom_id", "label": "ID Classroom"},
            {"key": "match_method", "label": "Método Vínculo"},
            {"key": "status", "label": "Situação Cadastral"},
        ]
        orphans = 0
        for s in students:
            if s["status_cotemig"] in ("ORFAO_CLASSROOM", "ORFAO_COTEMIG"):
                orphans += 1
            rows.append({
                "student": s["full_name"],
                "email": s["email"] or "-",
                "ra": s["cotemig_ra"] or "-",
                "classroom_id": s["classroom_user_id"] or "-",
                "match_method": s["match_method"],
                "status": s["status_cotemig"],
            })
        summary = {"total_alunos": len(students), "alunos_orfaos": orphans}

    elif code == "R12":
        columns = [
            {"key": "ra", "label": "Matrícula (RA)"},
            {"key": "student", "label": "Nome na Pauta"},
            {"key": "final_grade", "label": "Nota Final para Lançamento"},
        ]
        pauta = [s for s in students if s["cotemig_ra"]]
        pauta.sort(key=lambda x: x["full_name"])
        for s in pauta:
            rows.append({
                "ra": s["cotemig_ra"],
                "student": s["full_name"],
                "final_grade": s["total_points"],
            })
        summary = {"alunos_na_pauta": len(rows)}

    elif code == "R13":
        columns = [
            {"key": "ra", "label": "RA"},
            {"key": "student", "label": "Aluno"},
            {"key": "percentage", "label": "Aproveitamento (%)"},
            {"key": "pending_count", "label": "Pendências"},
            {"key": "risk_status", "label": "Classificação"},
        ]
        for s in students:
            if s["risk_status"] == "RISCO" or (s["percentage"] < course["min_passing_grade"] and s["pending_count"] >= 2):
                rows.append({
                    "ra": s["cotemig_ra"] or "-",
                    "student": s["full_name"],
                    "percentage": s["percentage"],
                    "pending_count": s["pending_count"],
                    "risk_status": s["risk_status"],
                })
        summary = {"alunos_em_risco": len(rows)}

    elif code == "R14":
        columns = [
            {"key": "ra", "label": "RA"},
            {"key": "student", "label": "Aluno"},
            {"key": "submission_rate", "label": "Taxa de Entrega (%)"},
            {"key": "percentage", "label": "Aproveitamento (%)"},
            {"key": "recommendation", "label": "Ação Sugerida"},
        ]
        for s in students:
            if s["submission_rate"] >= 70.0 and s["percentage"] < course["min_passing_grade"]:
                rows.append({
                    "ra": s["cotemig_ra"] or "-",
                    "student": s["full_name"],
                    "submission_rate": s["submission_rate"],
                    "percentage": s["percentage"],
                    "recommendation": "Monitoria / Reforço Técnico",
                })
        summary = {"total_identificados": len(rows)}

    elif code == "R15":
        columns = [
            {"key": "ra", "label": "RA"},
            {"key": "student", "label": "Aluno"},
            {"key": "delivered", "label": "Entregas Realizadas"},
            {"key": "pending_count", "label": "Atividades em Branco"},
            {"key": "avg_delivered_pct", "label": "Média nas Feitas (%)"},
        ]
        for s in students:
            delivered_ratios = []
            for a in activities:
                cell = s["activity_cells"].get(str(a["id"]), {})
                if cell.get("assigned_grade") is not None and a["classroom_max_points"] > 0:
                    delivered_ratios.append((cell["assigned_grade"] / a["classroom_max_points"]) * 100.0)
            avg_deliv = round(sum(delivered_ratios) / len(delivered_ratios), 1) if delivered_ratios else 0.0
            if avg_deliv >= 75.0 and s["pending_count"] >= 2:
                rows.append({
                    "ra": s["cotemig_ra"] or "-",
                    "student": s["full_name"],
                    "delivered": s["delivered_count"],
                    "pending_count": s["pending_count"],
                    "avg_delivered_pct": avg_deliv,
                })
        summary = {"total_identificados": len(rows)}

    return {
        "code": code,
        "title": meta["title"],
        "category": meta["category"],
        "description": meta["description"],
        "course_name": course["name"],
        "generated_at": now.isoformat(),
        "columns": columns,
        "rows": rows,
        "summary": summary,
        "chart_data": chart_data,
    }


def _generate_global_report(
    db: Session,
    code: str,
    meta: dict[str, str],
    now: datetime,
    course_map_id: int | None,
) -> dict[str, Any]:
    courses_q = db.query(CourseMapping)
    if course_map_id is not None and code != "R18":
        courses_q = courses_q.filter(CourseMapping.id == course_map_id)
    courses = courses_q.order_by(CourseMapping.name.asc()).all()

    columns: list[dict[str, str]] = []
    rows: list[dict[str, Any]] = []
    summary: dict[str, Any] = {}
    chart_data: list[dict[str, Any]] = []

    if code == "R16":
        columns = [
            {"key": "course", "label": "Turma"},
            {"key": "activity", "label": "Atividade"},
            {"key": "student", "label": "Aluno"},
            {"key": "updated_at", "label": "Entregue em"},
            {"key": "is_late", "label": "Atrasada?"},
        ]
        subs = (
            db.query(Submission, Activity, StudentMap, CourseMapping)
            .join(Activity, Submission.activity_id == Activity.id)
            .join(StudentMap, Submission.student_map_id == StudentMap.id)
            .join(CourseMapping, Activity.course_map_id == CourseMapping.id)
            .filter(Submission.state == "TURNED_IN", Submission.assigned_grade.is_(None))
            .order_by(Submission.updated_at.asc())
            .all()
        )
        for sub, act, st, crs in subs:
            if course_map_id is not None and crs.id != course_map_id:
                continue
            rows.append({
                "course": crs.name,
                "activity": act.title,
                "student": st.full_name,
                "updated_at": sub.updated_at.strftime("%Y-%m-%d %H:%M") if sub.updated_at else "-",
                "is_late": "Sim" if sub.is_late else "Não",
            })
        summary = {"pendentes_correcao": len(rows)}

    elif code == "R17":
        columns = [
            {"key": "course", "label": "Turma"},
            {"key": "activity", "label": "Atividade"},
            {"key": "student", "label": "Aluno"},
            {"key": "draft_grade", "label": "Nota em Rascunho"},
            {"key": "state", "label": "Status"},
        ]
        subs = (
            db.query(Submission, Activity, StudentMap, CourseMapping)
            .join(Activity, Submission.activity_id == Activity.id)
            .join(StudentMap, Submission.student_map_id == StudentMap.id)
            .join(CourseMapping, Activity.course_map_id == CourseMapping.id)
            .filter(Submission.draft_grade.is_not(None), Submission.assigned_grade.is_(None))
            .order_by(CourseMapping.name.asc(), Activity.title.asc())
            .all()
        )
        for sub, act, st, crs in subs:
            if course_map_id is not None and crs.id != course_map_id:
                continue
            rows.append({
                "course": crs.name,
                "activity": act.title,
                "student": st.full_name,
                "draft_grade": sub.draft_grade,
                "state": sub.state,
            })
        summary = {"rascunhos_nao_devolvidos": len(rows)}

    elif code == "R18":
        columns = [
            {"key": "course", "label": "Disciplina / Turma"},
            {"key": "students_count", "label": "Alunos"},
            {"key": "avg_percentage", "label": "Média Geral (%)"},
            {"key": "delivery_rate", "label": "Taxa de Entrega (%)"},
            {"key": "pending_grading", "label": "Aguardando Correção"},
            {"key": "at_risk", "label": "Em Risco"},
        ]
        total_students = 0
        total_pending_grading = 0
        total_at_risk = 0
        for crs in courses:
            gb = calculate_course_gradebook(db, crs.id, persist=False)
            sts = gb["students"]
            st_cnt = len(sts)
            avg_pct = round(sum(s["percentage"] for s in sts) / st_cnt, 1) if st_cnt else 0.0
            deliv_rate = round(sum(s["submission_rate"] for s in sts) / st_cnt, 1) if st_cnt else 0.0
            at_risk = sum(1 for s in sts if s["risk_status"] == "RISCO")
            pend_grad = (
                db.query(Submission)
                .join(Activity, Submission.activity_id == Activity.id)
                .filter(
                    Activity.course_map_id == crs.id,
                    Submission.state == "TURNED_IN",
                    Submission.assigned_grade.is_(None),
                )
                .count()
            )
            total_students += st_cnt
            total_pending_grading += pend_grad
            total_at_risk += at_risk
            rows.append({
                "course_id": crs.id,
                "course": crs.name,
                "students_count": st_cnt,
                "avg_percentage": avg_pct,
                "delivery_rate": deliv_rate,
                "pending_grading": pend_grad,
                "at_risk": at_risk,
            })
            chart_data.append({
                "name": crs.name[:24],
                "aproveitamento": avg_pct,
                "entrega": deliv_rate,
            })
        summary = {
            "total_turmas": len(courses),
            "total_alunos": total_students,
            "total_aguardando_correcao": total_pending_grading,
            "total_em_risco": total_at_risk,
        }

    return {
        "code": code,
        "title": meta["title"],
        "category": meta["category"],
        "description": meta["description"],
        "course_name": "Todas as Turmas" if code == "R18" or course_map_id is None else None,
        "generated_at": now.isoformat(),
        "columns": columns,
        "rows": rows,
        "summary": summary,
        "chart_data": chart_data,
    }


def export_report_csv(report: dict[str, Any]) -> bytes:
    output = io.StringIO()
    cols = report["columns"]
    writer = csv.writer(output, delimiter=";")
    writer.writerow([c["label"] for c in cols])
    for row in report["rows"]:
        writer.writerow([row.get(c["key"], "") for c in cols])
    return ("\ufeff" + output.getvalue()).encode("utf-8")


def export_report_xlsx(report: dict[str, Any]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = report["code"]

    ws.append([f"{report['code']} - {report['title']}"])
    ws.append([f"Turma: {report.get('course_name') or 'Geral'} | Gerado em: {report['generated_at'][:19]}"])
    ws.append([])

    cols = report["columns"]
    headers = [c["label"] for c in cols]
    ws.append(headers)

    header_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=4, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    for row in report["rows"]:
        ws.append([row.get(c["key"], "") for c in cols])

    for col_idx, c in enumerate(cols, start=1):
        max_len = max(
            [len(str(c["label"]))] + [len(str(r.get(c["key"], ""))) for r in report["rows"]]
        )
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max(max_len + 4, 14), 48)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def export_report_pdf(report: dict[str, Any]) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=24, rightMargin=24, topMargin=24, bottomMargin=24)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"<b>{report['code']} — {report['title']}</b>", styles["Title"]))
    elements.append(
        Paragraph(
            f"Turma: {report.get('course_name') or 'Geral'} | Gerado em: {report['generated_at'][:19]}",
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 12))

    cols = report["columns"]
    data = [[c["label"] for c in cols]]
    for r in report["rows"]:
        data.append([str(r.get(c["key"], ""))[:42] for c in cols])

    if len(data) == 1:
        data.append(["Sem registros para exibir"] + [""] * (len(cols) - 1))

    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    elements.append(table)
    doc.build(elements)
    return buf.getvalue()

