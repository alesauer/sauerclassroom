from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.academic import CourseMapping
from app.models.coursework import Activity, Theme
from app.schemas import CourseRulesUpdateRequest, ThemeCreateRequest
from app.services.calc_engine import calculate_course_gradebook

router = APIRouter(prefix="/api", tags=["Critérios e Grade de Notas"])


@router.get("/courses/{course_map_id}/gradebook")
def get_course_gradebook(course_map_id: int, db: Session = Depends(get_db)):
    try:
        return calculate_course_gradebook(db, course_map_id, persist=False)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/courses/{course_map_id}/themes")
def create_theme(
    course_map_id: int, payload: ThemeCreateRequest, db: Session = Depends(get_db)
):
    course = db.get(CourseMapping, course_map_id)
    if not course:
        raise HTTPException(status_code=404, detail="Turma não encontrada.")
    theme = Theme(
        course_map_id=course_map_id,
        title=payload.title,
        max_points_cap=payload.max_points_cap,
        rounding_rule=payload.rounding_rule,
        order_index=payload.order_index,
    )
    db.add(theme)
    db.commit()
    db.refresh(theme)
    return {
        "id": theme.id,
        "title": theme.title,
        "max_points_cap": theme.max_points_cap,
        "rounding_rule": theme.rounding_rule,
        "order_index": theme.order_index,
    }


@router.put("/courses/{course_map_id}/rules")
def update_course_rules(
    course_map_id: int, payload: CourseRulesUpdateRequest, db: Session = Depends(get_db)
):
    course = db.get(CourseMapping, course_map_id)
    if not course:
        raise HTTPException(status_code=404, detail="Turma não encontrada.")

    if payload.min_passing_grade is not None:
        course.min_passing_grade = payload.min_passing_grade
    if payload.use_draft_grades is not None:
        course.use_draft_grades = payload.use_draft_grades

    for tr in payload.themes:
        if tr.id is not None:
            theme = (
                db.query(Theme)
                .filter(Theme.id == tr.id, Theme.course_map_id == course_map_id)
                .first()
            )
            if theme:
                theme.title = tr.title
                theme.max_points_cap = tr.max_points_cap
                theme.rounding_rule = tr.rounding_rule
                theme.order_index = tr.order_index
        else:
            db.add(
                Theme(
                    course_map_id=course_map_id,
                    title=tr.title,
                    max_points_cap=tr.max_points_cap,
                    rounding_rule=tr.rounding_rule,
                    order_index=tr.order_index,
                )
            )

    for ar in payload.activities:
        act = (
            db.query(Activity)
            .filter(Activity.id == ar.id, Activity.course_map_id == course_map_id)
            .first()
        )
        if act:
            act.theme_id = ar.theme_id
            act.custom_points_weight = ar.custom_points_weight
            act.include_in_calc = ar.include_in_calc

    db.commit()
    return calculate_course_gradebook(db, course_map_id, persist=True)

