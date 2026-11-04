"""
Dịch vụ tính toán điểm học phần và GPA theo Quy chế Đào tạo Học viện Nông nghiệp Việt Nam (Điều 21 & Điều 22).
"""

from typing import Dict, Any, Optional, Tuple, List


# Bảng quy đổi thang điểm 10 sang thang điểm 4 và Điểm chữ (Điều 21 - Khoản 2)
# Mức điểm 10 làm tròn 1 chữ số thập phân
GRADE_SCALE = [
    {"letter": "A",  "gpa_4": 4.0, "min_score": 8.5, "max_score": 10.0, "status": "passed", "label": "Giỏi / Xuất sắc"},
    {"letter": "B+", "gpa_4": 3.5, "min_score": 8.0, "max_score": 8.4,  "status": "passed", "label": "Khá giỏi"},
    {"letter": "B",  "gpa_4": 3.0, "min_score": 7.0, "max_score": 7.9,  "status": "passed", "label": "Khá"},
    {"letter": "C+", "gpa_4": 2.5, "min_score": 6.5, "max_score": 6.9,  "status": "passed", "label": "Trung bình khá"},
    {"letter": "C",  "gpa_4": 2.0, "min_score": 5.5, "max_score": 6.4,  "status": "passed", "label": "Trung bình"},
    {"letter": "D+", "gpa_4": 1.5, "min_score": 5.0, "max_score": 5.4,  "status": "passed", "label": "Trung bình yếu"},
    {"letter": "D",  "gpa_4": 1.0, "min_score": 4.0, "max_score": 4.9,  "status": "passed", "label": "Yếu (Đạt tối thiểu)"},
    {"letter": "F",  "gpa_4": 0.0, "min_score": 0.0, "max_score": 3.9,  "status": "failed", "label": "Kém (Không đạt)"},
]


def score_to_letter_and_gpa(score_10: float) -> Tuple[str, float, str]:
    """
    Quy đổi điểm hệ 10 (đã làm tròn 1 chữ số thập phân) sang:
    (Điểm chữ, Điểm hệ 4, Trạng thái: passed/failed)
    """
    # Đảm bảo làm tròn 1 chữ số thập phân chuẩn
    rounded_score = round(score_10 + 1e-9, 1)

    for item in GRADE_SCALE:
        if rounded_score >= item["min_score"]:
            return item["letter"], item["gpa_4"], item["status"]

    return "F", 0.0, "failed"


def calculate_course_grade(components: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Tính điểm học phần dựa trên các điểm thành phần.
    components có cấu trúc:
    {
        "tp1": {"name": "Chuyên cần", "weight": 0.1, "score": 8.5},
        "tp2": {"name": "Giữa kỳ", "weight": 0.3, "score": 7.0},
        "tp3": {"name": "Cuối kỳ", "weight": 0.6, "score": 8.0} # hoặc score: None
    }
    """
    has_all_scores = True
    total_score = 0.0
    accumulated_weight = 0.0

    for _, comp in components.items():
        weight = float(comp.get("weight", 0.0))
        score = comp.get("score")

        if score is None:
            has_all_scores = False
        else:
            total_score += float(score) * weight
            accumulated_weight += weight

    if not has_all_scores:
        # Môn đang học dở dang, chưa có điểm tổng kết
        return {
            "total_score_10": None,
            "gpa_4": None,
            "letter_grade": None,
            "status": "in_progress",
            "is_complete": False,
        }

    # Làm tròn điểm hệ 10 đến 1 chữ số thập phân
    total_score_10 = round(total_score + 1e-9, 1)
    letter, gpa_4, status = score_to_letter_and_gpa(total_score_10)

    return {
        "total_score_10": total_score_10,
        "gpa_4": gpa_4,
        "letter_grade": letter,
        "status": status,
        "is_complete": True,
    }


def calculate_required_final_score(
    components: Dict[str, Dict[str, Any]],
    target_letter: Optional[str] = None
) -> Dict[str, Any]:
    """
    Tính điểm thi kết thúc học phần (TP3) tối thiểu cần đạt để đạt các mốc điểm chữ mong muốn.
    Giả định TP3 là thành phần có score=None hoặc tên comp chứa "cuối kỳ" / "tp3".
    """
    tp3_key = None
    tp3_weight = 0.6
    known_score_sum = 0.0

    for key, comp in components.items():
        weight = float(comp.get("weight", 0.0))
        score = comp.get("score")

        if score is None or key.lower() == "tp3" or "cuối kỳ" in comp.get("name", "").lower():
            tp3_key = key
            tp3_weight = weight
        else:
            known_score_sum += float(score) * weight

    if tp3_weight <= 0:
        return {"error": "Trọng số điểm thi cuối kỳ không hợp lệ (nhỏ hơn hoặc bằng 0)."}

    # Tính điểm TP3 cần đạt cho từng mức điểm chữ
    targets = []
    for scale in GRADE_SCALE:
        letter = scale["letter"]
        if letter == "F":
            continue

        target_min_10 = scale["min_score"]
        # target_min_10 <= known_score_sum + req_tp3 * tp3_weight
        # req_tp3 >= (target_min_10 - known_score_sum) / tp3_weight
        needed = (target_min_10 - known_score_sum) / tp3_weight
        needed_rounded = round(needed, 1)

        is_achievable = True
        status_msg = ""
        if needed_rounded <= 0.0:
            req_score = 0.0
            status_msg = "Chắc chắn đạt (chỉ cần thi không bị 0 điểm)"
        elif needed_rounded > 10.0:
            req_score = needed_rounded
            is_achievable = False
            status_msg = "Không khả thi (vượt quá thang điểm 10)"
        else:
            req_score = max(0.0, needed_rounded)
            status_msg = f"Cần thi tối thiểu {req_score:.1f} điểm"

        target_item = {
            "letter": letter,
            "gpa_4": scale["gpa_4"],
            "min_total_10": target_min_10,
            "required_final_score": req_score,
            "is_achievable": is_achievable,
            "note": status_msg,
        }
        targets.append(target_item)

    result = {
        "current_known_score_weighted": round(known_score_sum, 2),
        "final_exam_weight": tp3_weight,
        "targets": targets,
    }

    if target_letter:
        target_upper = target_letter.strip().upper()
        matched = next((t for t in targets if t["letter"] == target_upper), None)
        result["specific_target"] = matched

    return result


def calculate_gpa(courses_grades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Tính GPA học kỳ hoặc tích lũy dựa trên danh sách môn học có điểm.
    Chỉ tính các môn có status != 'in_progress' và có credits > 0.
    """
    total_credits = 0
    total_passed_credits = 0
    weighted_gpa4_sum = 0.0
    weighted_score10_sum = 0.0

    for cg in courses_grades:
        if cg.get("status") == "in_progress" or cg.get("gpa_4") is None:
            continue

        credits = int(cg.get("credits", 0))
        if credits <= 0:
            continue

        gpa_4 = float(cg.get("gpa_4", 0.0))
        score_10 = float(cg.get("total_score_10", 0.0))
        status = cg.get("status")

        total_credits += credits
        if status == "passed":
            total_passed_credits += credits

        weighted_gpa4_sum += gpa_4 * credits
        weighted_score10_sum += score_10 * credits

    if total_credits == 0:
        return {
            "total_credits": 0,
            "passed_credits": 0,
            "gpa_4": 0.0,
            "gpa_10": 0.0,
        }

    return {
        "total_credits": total_credits,
        "passed_credits": total_passed_credits,
        "gpa_4": round(weighted_gpa4_sum / total_credits, 2),
        "gpa_10": round(weighted_score10_sum / total_credits, 2),
    }
