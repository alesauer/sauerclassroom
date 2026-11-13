from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.report_service import (
    REPORT_CATALOG,
    export_report_csv,
    export_report_pdf,
    export_report_xlsx,
    generate_report,
)

router = APIRouter(prefix="/api/reports", tags=["Relatórios (R01–R18)"])


@router.get("/catalog")
def get_report_catalog():
    return REPORT_CATALOG


@router.get("/{report_code}")
def get_report_data(
    report_code: str,
    course_map_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    try:
        return generate_report(db, report_code, course_map_id=course_map_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{report_code}/export")
def export_report(
    report_code: str,
    format: str = Query(default="xlsx", pattern="^(xlsx|csv|pdf)$"),
    course_map_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    try:
        report = generate_report(db, report_code, course_map_id=course_map_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    code = report["code"]
    if format == "csv":
        content = export_report_csv(report)
        return Response(
            content=content,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{code}_relatorio.csv"'},
        )
    if format == "xlsx":
        content = export_report_xlsx(report)
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{code}_relatorio.xlsx"'},
        )
    content = export_report_pdf(report)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{code}_relatorio.pdf"'},
    )

