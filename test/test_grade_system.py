import pytest
from services.grade_calculator import (
    score_to_letter_and_gpa,
    calculate_course_grade,
    calculate_required_final_score,
    calculate_gpa,
)
from services.data_loader import (
    load_grades,
    load_class_grades,
    get_student_grades_summary,
    update_grade_component,
)
from services.academic_rules import get_candidate_courses


def test_score_to_letter_and_gpa():
    # Kiểm tra các mốc ranh giới chuẩn Điều 21
    assert score_to_letter_and_gpa(8.5) == ("A", 4.0, "passed")
    assert score_to_letter_and_gpa(8.4) == ("B+", 3.5, "passed")
    assert score_to_letter_and_gpa(8.0) == ("B+", 3.5, "passed")
    assert score_to_letter_and_gpa(7.9) == ("B", 3.0, "passed")
    assert score_to_letter_and_gpa(7.0) == ("B", 3.0, "passed")
    assert score_to_letter_and_gpa(6.9) == ("C+", 2.5, "passed")
    assert score_to_letter_and_gpa(6.5) == ("C+", 2.5, "passed")
    assert score_to_letter_and_gpa(6.4) == ("C", 2.0, "passed")
    assert score_to_letter_and_gpa(5.5) == ("C", 2.0, "passed")
    assert score_to_letter_and_gpa(5.4) == ("D+", 1.5, "passed")
    assert score_to_letter_and_gpa(5.0) == ("D+", 1.5, "passed")
    assert score_to_letter_and_gpa(4.9) == ("D", 1.0, "passed")
    assert score_to_letter_and_gpa(4.0) == ("D", 1.0, "passed")
    assert score_to_letter_and_gpa(3.9) == ("F", 0.0, "failed")
    assert score_to_letter_and_gpa(0.0) == ("F", 0.0, "failed")


def test_calculate_course_grade():
    # Trường hợp 1: Có đầy đủ 3 đầu điểm (TP1: 10%, TP2: 30%, TP3: 60%)
    comps_full = {
        "tp1": {"name": "Chuyên cần", "weight": 0.1, "score": 9.0},
        "tp2": {"name": "Giữa kỳ", "weight": 0.3, "score": 8.0},
        "tp3": {"name": "Cuối kỳ", "weight": 0.6, "score": 8.5},
    }
    # 9.0*0.1 + 8.0*0.3 + 8.5*0.6 = 0.9 + 2.4 + 5.1 = 8.4 -> B+
    res_full = calculate_course_grade(comps_full)
    assert res_full["is_complete"] is True
    assert res_full["total_score_10"] == 8.4
    assert res_full["letter_grade"] == "B+"
    assert res_full["gpa_4"] == 3.5
    assert res_full["status"] == "passed"

    # Trường hợp 2: Môn đang học dở dang (chưa có điểm cuối kỳ)
    comps_progress = {
        "tp1": {"name": "Chuyên cần", "weight": 0.1, "score": 8.5},
        "tp2": {"name": "Giữa kỳ", "weight": 0.3, "score": 6.0},
        "tp3": {"name": "Cuối kỳ", "weight": 0.6, "score": None},
    }
    res_progress = calculate_course_grade(comps_progress)
    assert res_progress["is_complete"] is False
    assert res_progress["status"] == "in_progress"
    assert res_progress["total_score_10"] is None


def test_calculate_required_final_score():
    # TP1=8.5 (10%), TP2=6.0 (30%) -> Đã có: 0.85 + 1.80 = 2.65
    # Để đạt A (>= 8.5): cần thi (8.5 - 2.65) / 0.6 = 5.85 / 0.6 = 9.75 -> cần ~9.8
    comps = {
        "tp1": {"name": "Chuyên cần", "weight": 0.1, "score": 8.5},
        "tp2": {"name": "Giữa kỳ", "weight": 0.3, "score": 6.0},
        "tp3": {"name": "Cuối kỳ", "weight": 0.6, "score": None},
    }
    res = calculate_required_final_score(comps, target_letter="A")
    assert res["final_exam_weight"] == 0.6
    assert "targets" in res

    specific = res["specific_target"]
    assert specific is not None
    assert specific["letter"] == "A"
    assert specific["is_achievable"] is True
    assert 9.7 <= specific["required_final_score"] <= 9.8


def test_data_loader_grades():
    # Test load bảng điểm sinh viên 671234
    grades_671234 = load_grades("671234")
    assert len(grades_671234) > 0

    # Phải có môn đang học (in_progress) và môn đã hoàn thành
    statuses = {g["status"] for g in grades_671234}
    assert "in_progress" in statuses
    assert "passed" in statuses

    # Test load lớp học phần TH02001_01 (Cơ sở dữ liệu)
    class_grades = load_class_grades("TH02001_01")
    assert len(class_grades) >= 2  # có cả 671234, 671235, 680001


def test_student_grades_summary():
    summary = get_student_grades_summary("671234")
    assert summary["student_id"] == "671234"
    assert len(summary["in_progress_courses"]) >= 1
    assert len(summary["completed_courses"]) >= 1
    assert summary["accumulated_credits"] > 0
    assert summary["cumulative_gpa_4"] > 0.0


def test_backward_compatibility_scheduler():
    # Đảm bảo hàm xếp lịch cốt lõi không bị ảnh hưởng
    candidates = get_candidate_courses("671234", allow_early=True)
    assert len(candidates) > 0
    # Môn trượt TH01007 phải có priority = 1 (retake)
    failed_candidates = [c for c in candidates if c["code"] == "TH01007"]
    assert len(failed_candidates) == 1
    assert failed_candidates[0]["priority"] == 1
    assert failed_candidates[0]["reason"] == "retake"
