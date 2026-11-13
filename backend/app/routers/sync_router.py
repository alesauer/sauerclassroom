from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.academic import CourseMapping, StudentMap, SyncHistory
from app.schemas import CourseMappingCreate, CourseMappingUpdate, StudentLinkRequest
from app.services.sync_service import SyncService, seed_demo_data

router = APIRouter(prefix="/api", tags=["Sincronização e Vínculos"])


@router.get("/courses")
def list_courses(db: Session = Depends(get_db)):
    courses = db.query(CourseMapping).order_by(CourseMapping.name.asc()).all()
    return [
        {
            "id": c.id,
            "classroom_course_id": c.classroom_course_id,
            "cotemig_class_id": c.cotemig_class_id,
            "name": c.name,
            "section": c.section,
            "term_period": c.term_period,
            "min_passing_grade": c.min_passing_grade,
            "use_draft_grades": c.use_draft_grades,
            "last_sync_at": c.last_sync_at.isoformat() if c.last_sync_at else None,
            "students_count": len(c.students),
            "activities_count": len(c.activities),
        }
        for c in courses
    ]


@router.post("/courses/mapping")
def create_course_mapping(payload: CourseMappingCreate, db: Session = Depends(get_db)):
    existing = None
    if payload.classroom_course_id:
        existing = (
            db.query(CourseMapping)
            .filter(CourseMapping.classroom_course_id == payload.classroom_course_id)
            .first()
        )
    if existing:
        existing.cotemig_class_id = payload.cotemig_class_id
        existing.name = payload.name
        existing.section = payload.section
        existing.term_period = payload.term_period
        existing.min_passing_grade = payload.min_passing_grade
        existing.use_draft_grades = payload.use_draft_grades
        db.commit()
        db.refresh(existing)
        return {"id": existing.id, "status": "updated"}

    course = CourseMapping(
        classroom_course_id=payload.classroom_course_id,
        cotemig_class_id=payload.cotemig_class_id,
        name=payload.name,
        section=payload.section,
        term_period=payload.term_period,
        min_passing_grade=payload.min_passing_grade,
        use_draft_grades=payload.use_draft_grades,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return {"id": course.id, "status": "created"}


@router.put("/courses/{course_map_id}")
def update_course_mapping(
    course_map_id: int, payload: CourseMappingUpdate, db: Session = Depends(get_db)
):
    course = db.get(CourseMapping, course_map_id)
    if not course:
        raise HTTPException(status_code=404, detail="Turma não encontrada.")
    for field, val in payload.model_dump(exclude_unset=True).items():
        setattr(course, field, val)
    db.commit()
    return {"id": course.id, "status": "updated"}


@router.get("/courses/{course_map_id}/students")
def list_course_students(course_map_id: int, db: Session = Depends(get_db)):
    students = (
        db.query(StudentMap)
        .filter(StudentMap.course_map_id == course_map_id)
        .order_by(StudentMap.full_name.asc())
        .all()
    )
    return [
        {
            "id": s.id,
            "classroom_user_id": s.classroom_user_id,
            "cotemig_ra": s.cotemig_ra,
            "full_name": s.full_name,
            "email": s.email,
            "status_cotemig": s.status_cotemig,
            "match_method": s.match_method,
        }
        for s in students
    ]


@router.post("/courses/{course_map_id}/students/link")
def link_student_manually(
    course_map_id: int, payload: StudentLinkRequest, db: Session = Depends(get_db)
):
    student = (
        db.query(StudentMap)
        .filter(StudentMap.id == payload.student_map_id, StudentMap.course_map_id == course_map_id)
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Aluno não encontrado nesta turma.")
    if payload.cotemig_ra is not None:
        student.cotemig_ra = payload.cotemig_ra
    if payload.classroom_user_id is not None:
        student.classroom_user_id = payload.classroom_user_id
    student.status_cotemig = payload.status_cotemig
    student.match_method = "manual"
    db.commit()
    return {"status": "linked", "student_id": student.id}


@router.get("/sync/courses/external")
def list_external_courses():
    return SyncService().list_external_sources()


@router.post("/sync/course/{course_map_id}")
def sync_single_course(course_map_id: int, db: Session = Depends(get_db)):
    try:
        return SyncService().sync_course(db, course_map_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/sync/all")
def sync_all_courses(db: Session = Depends(get_db)):
    courses = db.query(CourseMapping).all()
    svc = SyncService()
    results = [svc.sync_course(db, c.id) for c in courses]
    return {"synced_courses": len(results), "results": results}


@router.post("/sync/demo-seed")
def trigger_demo_seed(db: Session = Depends(get_db)):
    return seed_demo_data(db)


@router.get("/sync/history")
def get_sync_history(db: Session = Depends(get_db)):
    items = db.query(SyncHistory).order_by(SyncHistory.synced_at.desc()).limit(25).all()
    return [
        {
            "id": h.id,
            "course_map_id": h.course_map_id,
            "source": h.source,
            "status": h.status,
            "details": h.details,
            "synced_at": h.synced_at.isoformat(),
        }
        for h in items
    ]

