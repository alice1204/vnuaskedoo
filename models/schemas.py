from typing import Optional, List, Dict, Any
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class ScheduleRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    target_credits: int = Field(
        default=18,
        ge=15,
        le=25,
    )

    allow_early: bool = True


class ExplainScheduleRequest(BaseModel):
    schedule_result: dict


class ChatMessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default_session"


class ChatResponse(BaseModel):
    response: str
    session_id: str
    tools_called: Optional[List[str]] = []


# ==============================================================================
# SCHEMAS CHO HỆ THỐNG QUẢN LÝ ĐIỂM SỐ & TƯ VẤN KẾT QUẢ HỌC TẬP
# ==============================================================================

class ScoreComponent(BaseModel):
    name: str = Field(..., description="Tên đầu điểm: Chuyên cần, Giữa kỳ, Thi kết thúc...")
    weight: float = Field(..., ge=0.0, le=1.0, description="Trọng số đầu điểm (0.0 - 1.0)")
    score: Optional[float] = Field(None, ge=0.0, le=10.0, description="Điểm số hệ 10, None nếu chưa có")


class CourseGrade(BaseModel):
    student_id: str
    course_code: str
    course_name: str
    class_code: Optional[str] = None
    semester: int
    academic_year: Optional[str] = None
    credits: int = Field(default=3, ge=1)
    components: Dict[str, ScoreComponent] = Field(
        default_factory=dict,
        description="Dictionary các đầu điểm tp1, tp2, tp3..."
    )
    total_score_10: Optional[float] = None
    gpa_4: Optional[float] = None
    letter_grade: Optional[str] = None
    status: str = Field(
        default="in_progress",
        description="Trạng thái: in_progress (đang học), passed (đạt), failed (học lại)"
    )


class StudentGradesSummary(BaseModel):
    student_id: str
    student_name: Optional[str] = None
    major: Optional[str] = None
    current_semester: Optional[int] = None
    accumulated_credits: int = 0
    passed_credits: int = 0
    cumulative_gpa_4: float = 0.0
    cumulative_gpa_10: float = 0.0
    in_progress_courses: List[CourseGrade] = []
    completed_courses: List[CourseGrade] = []
    failed_courses: List[CourseGrade] = []


class UpdateGradeRequest(BaseModel):
    student_id: str
    course_code: str
    class_code: Optional[str] = None
    component_key: str = Field(..., description="Mã đầu điểm, ví dụ: tp1, tp2, tp3")
    score: float = Field(..., ge=0.0, le=10.0, description="Điểm chấm hệ 10 (0.0 - 10.0)")


class TargetScoreRequest(BaseModel):
    student_id: Optional[str] = None
    course_code: str
    target_letter: Optional[str] = Field(None, description="Điểm chữ mục tiêu: A, B+, B, C+, C, D+, D")


class TargetScoreItem(BaseModel):
    letter: str
    gpa_4: float
    min_total_10: float
    required_final_score: float
    is_achievable: bool
    note: str


class TargetScoreResponse(BaseModel):
    course_code: str
    course_name: str
    current_known_score_weighted: float
    final_exam_weight: float
    targets: List[TargetScoreItem]
    specific_target: Optional[TargetScoreItem] = None

