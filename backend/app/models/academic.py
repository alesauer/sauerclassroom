from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CourseMapping(Base):
    __tablename__ = "courses_mapping"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    classroom_course_id: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    cotemig_class_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    section: Mapped[str | None] = mapped_column(String(128), nullable=True)
    term_period: Mapped[str] = mapped_column(String(64), default="2026/2")
    min_passing_grade: Mapped[float] = mapped_column(Float, default=60.0)
    use_draft_grades: Mapped[bool] = mapped_column(Boolean, default=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    students: Mapped[list["StudentMap"]] = relationship(
        "StudentMap", back_populates="course", cascade="all, delete-orphan"
    )
    themes: Mapped[list["Theme"]] = relationship(
        "Theme", back_populates="course", cascade="all, delete-orphan"
    )
    activities: Mapped[list["Activity"]] = relationship(
        "Activity", back_populates="course", cascade="all, delete-orphan"
    )
    cotemig_snapshots: Mapped[list["CotemigGradeSnapshot"]] = relationship(
        "CotemigGradeSnapshot", back_populates="course", cascade="all, delete-orphan"
    )


class StudentMap(Base):
    __tablename__ = "students_map"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_map_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("courses_mapping.id", ondelete="CASCADE"), nullable=False, index=True
    )
    classroom_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    cotemig_ra: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    status_cotemig: Mapped[str] = mapped_column(String(64), default="ATIVO")
    match_method: Mapped[str] = mapped_column(String(32), default="unmatched")

    course: Mapped["CourseMapping"] = relationship("CourseMapping", back_populates="students")
    submissions: Mapped[list["Submission"]] = relationship(
        "Submission", back_populates="student", cascade="all, delete-orphan"
    )


class CotemigGradeSnapshot(Base):
    __tablename__ = "cotemig_grades_snapshot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_map_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("courses_mapping.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_map_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("students_map.id", ondelete="SET NULL"), nullable=True
    )
    cotemig_ra: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    student_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stage_name: Mapped[str] = mapped_column(String(64), default="Etapa 1")
    official_grade: Mapped[float] = mapped_column(Float, default=0.0)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    course: Mapped["CourseMapping"] = relationship(
        "CourseMapping", back_populates="cotemig_snapshots"
    )


class SyncHistory(Base):
    __tablename__ = "sync_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_map_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("courses_mapping.id", ondelete="SET NULL"), nullable=True
    )
    source: Mapped[str] = mapped_column(String(32), default="all")
    status: Mapped[str] = mapped_column(String(32), default="success")
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

