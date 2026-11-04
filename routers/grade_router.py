from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query

from models.schemas import (
    StudentGradesSummary,
    UpdateGradeRequest,
    TargetScoreRequest,
    TargetScoreResponse,
    TargetScoreItem,
)
from services.student_service import (
    get_current_student_id,
    get_current_teacher_id,
)
from services.academic_rules import get_student
from services.data_loader import (
    load_grades,
    get_student_grades_summary,
    update_grade_component,
)
from services.grade_calculator import (
    calculate_required_final_score,
)
from services.teacher_service import (
    get_teacher_classes,
    get_class_grade_details,
    get_class_grade_stats,
)

router = APIRouter(prefix="/api", tags=["Grades & Academic Advising"])


# ==============================================================================
# 1. API DÀNH CHO SINH VIÊN (STUDENT APIS)
# ==============================================================================

@router.get("/student/grades", response_model=StudentGradesSummary)
def get_my_grades(
    student_id: Optional[str] = None,
    current_id: str = Depends(get_current_student_id),
):
    """
    Lấy toàn bộ bảng điểm cá nhân của sinh viên:
    - Danh sách môn đang học kỳ này (đang chờ thi cuối kỳ).
    - Danh sách môn đã hoàn thành và môn bị trượt.
    - Tổng tín chỉ tích lũy, GPA hệ 4 và GPA hệ 10.
    """
    target_student_id = student_id or current_id
    student_profile = get_student(target_student_id)

    if not student_profile:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy hồ sơ sinh viên có mã {target_student_id}",
        )

    summary = get_student_grades_summary(target_student_id)
    summary["student_name"] = student_profile.get("name")
    summary["major"] = student_profile.get("major")
    summary["current_semester"] = student_profile.get("current_semester")

    return summary


@router.post("/student/target-score", response_model=TargetScoreResponse)
def calculate_target_exam_score(
    request: TargetScoreRequest,
    current_id: str = Depends(get_current_student_id),
):
    """
    Tính toán điểm thi kết thúc học phần (TP3) tối thiểu cần đạt
    để đạt các mốc điểm chữ mong muốn (A, B+, B, C+, C, D).
    """
    target_student_id = request.student_id or current_id
    grades = load_grades(target_student_id)

    course_grade = next(
        (g for g in grades if g.get("course_code", "").upper() == request.course_code.upper()),
        None
    )

    if not course_grade:
        raise HTTPException(
            status_code=404,
            detail=f"Sinh viên {target_student_id} chưa đăng ký học phần {request.course_code}",
        )

    components = course_grade.get("components", {})
    calc_result = calculate_required_final_score(components, target_letter=request.target_letter)

    if "error" in calc_result:
        raise HTTPException(status_code=400, detail=calc_result["error"])

    target_items = [
        TargetScoreItem(
            letter=t["letter"],
            gpa_4=t["gpa_4"],
            min_total_10=t["min_total_10"],
            required_final_score=t["required_final_score"],
            is_achievable=t["is_achievable"],
            note=t["note"],
        )
        for t in calc_result["targets"]
    ]

    specific_item = None
    if calc_result.get("specific_target"):
        st = calc_result["specific_target"]
        specific_item = TargetScoreItem(
            letter=st["letter"],
            gpa_4=st["gpa_4"],
            min_total_10=st["min_total_10"],
            required_final_score=st["required_final_score"],
            is_achievable=st["is_achievable"],
            note=st["note"],
        )

    return TargetScoreResponse(
        course_code=course_grade.get("course_code"),
        course_name=course_grade.get("course_name", request.course_code),
        current_known_score_weighted=calc_result["current_known_score_weighted"],
        final_exam_weight=calc_result["final_exam_weight"],
        targets=target_items,
        specific_target=specific_item,
    )


@router.get("/student/academic-warning")
def get_academic_warning(
    student_id: Optional[str] = None,
    current_id: str = Depends(get_current_student_id),
):
    """
    Kiểm tra và cảnh báo sớm các nguy cơ học vụ:
    - Cảnh báo cấm thi: Nếu điểm chuyên cần (TP1) < 5.0.
    - Cảnh báo rớt môn: Nếu điểm giữa kỳ (TP2) quá thấp (< 4.0).
    - Cảnh báo học vụ tích lũy: Nếu GPA hệ 4 dưới ngưỡng an toàn theo quy chế.
    """
    target_student_id = student_id or current_id
    summary = get_student_grades_summary(target_student_id)

    warnings = []
    in_progress = summary.get("in_progress_courses", [])

    for course in in_progress:
        components = course.get("components", {})
        c_code = course.get("course_code")
        c_name = course.get("course_name")

        tp1_score = components.get("tp1", {}).get("score")
        tp2_score = components.get("tp2", {}).get("score")

        if tp1_score is not None and tp1_score < 5.0:
            warnings.append({
                "type": "attendance_risk",
                "severity": "danger",
                "course_code": c_code,
                "course_name": c_name,
                "message": f"Điểm chuyên cần đạt {tp1_score}/10. Nguy cơ rất cao bị CẤM THI kết thúc học phần theo Quy chế!",
                "recommendation": "Liên hệ ngay với giảng viên bộ môn để kiểm tra lại tình trạng điểm danh và làm bù nhiệm vụ học tập.",
            })
        elif tp2_score is not None and tp2_score < 4.0:
            warnings.append({
                "type": "exam_risk",
                "severity": "warning",
                "course_code": c_code,
                "course_name": c_name,
                "message": f"Điểm giữa kỳ đạt {tp2_score}/10. Nguy cơ trượt môn cao nếu không có kế hoạch ôn thi bứt phá.",
                "recommendation": "Cần tập trung ôn luyện để đạt điểm thi cuối kỳ cao nhằm kéo điểm trung bình môn.",
            })

    # Đánh giá GPA tích lũy
    gpa_4 = summary.get("cumulative_gpa_4", 0.0)
    passed_credits = summary.get("passed_credits", 0)
    failed_courses = summary.get("failed_courses", [])

    if gpa_4 > 0 and gpa_4 < 1.5:
        warnings.append({
            "type": "gpa_warning",
            "severity": "danger",
            "course_code": None,
            "course_name": None,
            "message": f"Điểm trung bình tích lũy hiện tại là {gpa_4}/4.0, tiệm cận ngưỡng bị cảnh báo học tập mức 1!",
            "recommendation": "Cần ưu tiên đăng ký học lại các môn bị điểm F và học cải thiện điểm D để nâng GPA.",
        })

    return {
        "student_id": target_student_id,
        "cumulative_gpa_4": gpa_4,
        "passed_credits": passed_credits,
        "failed_count": len(failed_courses),
        "total_warnings": len(warnings),
        "warnings": warnings,
        "is_safe": len(warnings) == 0,
    }


# ==============================================================================
# 2. API DÀNH CHO GIẢNG VIÊN (TEACHER APIS)
# ==============================================================================

@router.get("/teacher/classes")
def get_my_classes(
    teacher_id: Optional[str] = None,
    current_teacher: str = Depends(get_current_teacher_id),
):
    """
    Lấy danh sách các lớp học phần do giảng viên phụ trách kèm theo sĩ số và tiến độ điểm.
    """
    target_teacher_id = teacher_id or current_teacher
    classes = get_teacher_classes(target_teacher_id)
    return {
        "teacher_id": target_teacher_id,
        "total_classes": len(classes),
        "classes": classes,
    }


@router.get("/teacher/classes/{class_code}/grades")
def get_class_gradebook(class_code: str):
    """
    Lấy sổ điểm điện tử của lớp học phần bao gồm danh sách toàn bộ sinh viên,
    các đầu điểm thành phần TP1, TP2, TP3, điểm tổng kết 10, điểm chữ và trạng thái.
    """
    students_grades = get_class_grade_details(class_code)
    if not students_grades:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy dữ liệu điểm cho lớp học phần {class_code}",
        )

    return {
        "class_code": class_code,
        "total_students": len(students_grades),
        "grades": students_grades,
    }


@router.post("/teacher/grades/update")
def update_grade(request: UpdateGradeRequest):
    """
    Giảng viên nhập hoặc cập nhật điểm thành phần (tp1, tp2, tp3) cho một sinh viên.
    Hệ thống sẽ tự động tính toán lại điểm tổng kết hệ 10, điểm chữ và trạng thái.
    """
    try:
        updated = update_grade_component(
            student_id=request.student_id,
            course_code=request.course_code,
            component_key=request.component_key,
            new_score=request.score,
            class_code=request.class_code,
        )
        return {
            "success": True,
            "message": f"Đã cập nhật điểm {request.component_key} cho sinh viên {request.student_id} thành công.",
            "data": updated,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi cập nhật điểm: {str(e)}")


@router.get("/teacher/classes/{class_code}/stats")
def get_class_statistics(class_code: str):
    """
    Báo cáo phân tích phổ điểm của lớp học phần:
    - Điểm trung bình, cao nhất, thấp nhất.
    - Phổ điểm chữ A, B+, B, C+, C, D+, D, F.
    - Tỷ lệ đạt / trượt.
    - Danh sách sinh viên có nguy cơ cấm thi hoặc điểm thấp.
    """
    stats = get_class_grade_stats(class_code)
    if stats.get("total_students", 0) == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy dữ liệu thống kê cho lớp học phần {class_code}",
        )

    return stats
