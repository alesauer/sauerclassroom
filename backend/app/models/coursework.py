from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Theme(Base):
    __tablename__ = "themes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_map_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("courses_mapping.id", ondelete="CASCADE"), nullable=False, index=True
    )
    classroom_topic_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    max_points_cap: Mapped[float | None] = mapped_column(Float, nullable=True)
    rounding_rule: Mapped[str] = mapped_column(String(32), default="decimal_1")
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    course: Mapped["CourseMapping"] = relationship("CourseMapping", back_populates="themes")
    activities: Mapped[list["Activity"]] = relationship("Activity", back_populates="theme")


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_map_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("courses_mapping.id", ondelete="CASCADE"), nullable=False, index=True
    )
    theme_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("themes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    classroom_work_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    classroom_max_points: Mapped[float] = mapped_column(Float, default=100.0)
    custom_points_weight: Mapped[float] = mapped_column(Float, default=10.0)
    include_in_calc: Mapped[bool] = mapped_column(Boolean, default=True)
    work_type: Mapped[str] = mapped_column(String(64), default="ASSIGNMENT")

    course: Mapped["CourseMapping"] = relationship("CourseMapping", back_populates="activities")
    theme: Mapped["Theme | None"] = relationship("Theme", back_populates="activities")
    submissions: Mapped[list["Submission"]] = relationship(
        "Submission", back_populates="activity", cascade="all, delete-orphan"
    )


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    activity_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("activities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_map_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("students_map.id", ondelete="CASCADE"), nullable=False, index=True
    )
    state: Mapped[str] = mapped_column(String(32), default="NEW")
    is_late: Mapped[bool] = mapped_column(Boolean, default=False)
    has_attachments: Mapped[bool] = mapped_column(Boolean, default=True)
    assigned_grade: Mapped[float | None] = mapped_column(Float, nullable=True)
    draft_grade: Mapped[float | None] = mapped_column(Float, nullable=True)
    calculated_points: Mapped[float] = mapped_column(Float, default=0.0)
    turned_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    activity: Mapped["Activity"] = relationship("Activity", back_populates="submissions")
    student: Mapped["StudentMap"] = relationship("StudentMap", back_populates="submissions")

