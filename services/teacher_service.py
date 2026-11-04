"""
Dịch vụ quản lý lớp học và phân tích điểm số dành cho Giảng viên.
"""

from typing import List, Dict, Any, Optional
from collections import Counter
from services.data_loader import load_class_grades, load_students, load_grades
from services.grade_calculator import GRADE_SCALE


# Dữ liệu danh mục lớp học phần phân công cho giảng viên (Mock Teacher Classes)
TEACHER_ASSIGNMENTS = {
    "GV001": [
        {
            "class_code": "TH02001_01",
            "course_code": "TH02001",
            "course_name": "Cơ sở dữ liệu",
            "credits": 3,
            "semester": "2024-2025-2",
            "schedule": "T2(1-3)",
            "room": "ND201",
        },
        {
            "class_code": "TH02015_301",
            "course_code": "TH02015",
            "course_name": "Nguyên lý hệ điều hành",
            "credits": 3,
            "semester": "2024-2025-2",
            "schedule": "T5(1-3)",
            "room": "ND102",
        },
        {
            "class_code": "TH01007_03",
            "course_code": "TH01007",
            "course_name": "Xác suất thống kê",
            "credits": 3,
            "semester": "2023-2024-2",
            "schedule": "T4(4-5)",
            "room": "ND305",
        },
    ]
}


def get_teacher_classes(teacher_id: str = "GV001") -> List[Dict[str, Any]]:
    """
    Lấy danh sách các lớp học phần được phân công cho giảng viên,
    kèm theo thống kê nhanh sĩ số sinh viên trong từng lớp.
    """
    classes = TEACHER_ASSIGNMENTS.get(str(teacher_id), [])
    result = []

    for c in classes:
        class_code = c["class_code"]
        enrolled_students = load_class_grades(class_code)
        completed_count = sum(1 for s in enrolled_students if s.get("status") in ("passed", "failed"))

        item = {
            **c,
            "total_students": len(enrolled_students),
            "completed_students": completed_count,
            "in_progress_students": len(enrolled_students) - completed_count,
        }
        result.append(item)

    return result


def get_class_grade_details(class_code: str) -> List[Dict[str, Any]]:
    """
    Lấy danh sách sinh viên kèm bảng điểm chi tiết trong một lớp học phần.
    Tự động ghép tên sinh viên từ hồ sơ sinh viên.
    """
    records = load_class_grades(class_code)
    students_data = load_students().get("students", {})

    enhanced_records = []
    for r in records:
        s_id = str(r.get("student_id"))
        s_profile = students_data.get(s_id, {})
        enhanced_records.append({
            **r,
            "student_name": s_profile.get("name", f"Sinh viên {s_id}"),
            "major": s_profile.get("major", ""),
            "cohort": s_profile.get("cohort", ""),
        })

    # Sắp xếp theo MSSV
    enhanced_records.sort(key=lambda x: x.get("student_id", ""))
    return enhanced_records


def get_class_grade_stats(class_code: str) -> Dict[str, Any]:
    """
    Phân tích và thống kê phổ điểm của một lớp học phần:
    - Sĩ số, điểm trung bình, điểm cao nhất, điểm thấp nhất
    - Phổ điểm chữ: A, B+, B, C+, C, D+, D, F
    - Tỷ lệ đạt / trượt
    - Danh sách sinh viên có nguy cơ cấm thi (TP1 < 5.0)
    """
    records = get_class_grade_details(class_code)
    total_students = len(records)

    if total_students == 0:
        return {
            "class_code": class_code,
            "total_students": 0,
            "message": "Lớp học phần hiện chưa có sinh viên đăng ký.",
        }

    # Đếm phổ điểm chữ
    letter_counts = {scale["letter"]: 0 for scale in GRADE_SCALE}
    scores_10 = []
    passed_count = 0
    failed_count = 0
    in_progress_count = 0
    at_risk_students = []

    for r in records:
        components = r.get("components", {})
        tp1_score = components.get("tp1", {}).get("score")
        tp2_score = components.get("tp2", {}).get("score")
        status = r.get("status")

        # Cảnh báo sinh viên có nguy cơ cấm thi (Chuyên cần < 5.0 hoặc nghỉ nhiều)
        if tp1_score is not None and tp1_score < 5.0:
            at_risk_students.append({
                "student_id": r.get("student_id"),
                "student_name": r.get("student_name"),
                "reason": f"Điểm chuyên cần thấp ({tp1_score}/10) - Nguy cơ bị cấm thi",
                "tp1_score": tp1_score,
                "tp2_score": tp2_score,
            })
        elif tp2_score is not None and tp2_score < 4.0:
            at_risk_students.append({
                "student_id": r.get("student_id"),
                "student_name": r.get("student_name"),
                "reason": f"Điểm giữa kỳ thấp ({tp2_score}/10) - Nguy cơ trượt môn cao",
                "tp1_score": tp1_score,
                "tp2_score": tp2_score,
            })

        if status == "in_progress":
            in_progress_count += 1
            continue

        score_10 = r.get("total_score_10")
        letter = r.get("letter_grade")

        if score_10 is not None:
            scores_10.append(score_10)

        if letter in letter_counts:
            letter_counts[letter] += 1

        if status == "passed":
            passed_count += 1
        elif status == "failed":
            failed_count += 1

    completed_count = passed_count + failed_count
    avg_score_10 = round(sum(scores_10) / len(scores_10), 2) if scores_10 else None
    max_score_10 = max(scores_10) if scores_10 else None
    min_score_10 = min(scores_10) if scores_10 else None

    # Tỷ lệ phần trăm phổ điểm chữ
    letter_distribution = []
    for scale in GRADE_SCALE:
        letter = scale["letter"]
        count = letter_counts[letter]
        percent = round((count / completed_count * 100), 1) if completed_count > 0 else 0.0
        letter_distribution.append({
            "letter": letter,
            "label": scale["label"],
            "count": count,
            "percentage": percent,
        })

    return {
        "class_code": class_code,
        "total_students": total_students,
        "completed_count": completed_count,
        "in_progress_count": in_progress_count,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "pass_rate_percentage": round((passed_count / completed_count * 100), 1) if completed_count > 0 else 0.0,
        "average_score_10": avg_score_10,
        "max_score_10": max_score_10,
        "min_score_10": min_score_10,
        "letter_distribution": letter_distribution,
        "at_risk_students": at_risk_students,
    }
