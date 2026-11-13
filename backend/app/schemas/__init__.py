from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PlatformAuthStatus(BaseModel):
    connected: bool
    status: str  # Conectado | Expirado | Desconectado | Erro
    account: str | None = None
    mode: str | None = None
    details: str | None = None


class AuthStatusResponse(BaseModel):
    google_classroom: PlatformAuthStatus
    cotemig_portal: PlatformAuthStatus


class CotemigLoginRequest(BaseModel):
    username: str = Field(..., min_length=2)
    password: str = Field(..., min_length=2)


class CourseMappingCreate(BaseModel):
    classroom_course_id: str | None = None
    cotemig_class_id: str | None = None
    name: str
    section: str | None = None
    term_period: str = "2026/2"
    min_passing_grade: float = 60.0
    use_draft_grades: bool = False


class CourseMappingUpdate(BaseModel):
    cotemig_class_id: str | None = None
    name: str | None = None
    section: str | None = None
    term_period: str | None = None
    min_passing_grade: float | None = None
    use_draft_grades: bool | None = None


class StudentLinkRequest(BaseModel):
    student_map_id: int
    cotemig_ra: str | None = None
    classroom_user_id: str | None = None
    status_cotemig: str = "ATIVO"


class ThemeRuleUpdate(BaseModel):
    id: int | None = None
    title: str
    max_points_cap: float | None = None
    rounding_rule: str = "decimal_1"
    order_index: int = 0


class ActivityRuleUpdate(BaseModel):
    id: int
    theme_id: int | None = None
    custom_points_weight: float
    include_in_calc: bool = True


class CourseRulesUpdateRequest(BaseModel):
    min_passing_grade: float | None = None
    use_draft_grades: bool | None = None
    themes: list[ThemeRuleUpdate] = []
    activities: list[ActivityRuleUpdate] = []


class ThemeCreateRequest(BaseModel):
    title: str
    max_points_cap: float | None = None
    rounding_rule: str = "decimal_1"
    order_index: int = 0


class ReportPayload(BaseModel):
    code: str
    title: str
    category: str
    description: str
    course_name: str | None = None
    generated_at: datetime
    columns: list[dict[str, str]]
    rows: list[dict[str, Any]]
    summary: dict[str, Any] = {}
    chart_data: list[dict[str, Any]] = []

