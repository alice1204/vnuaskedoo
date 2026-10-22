import os
import yaml
from typing import Dict, List, Optional, Any

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))

# In-memory cache
_CURRICULUMS: Dict[str, dict] = {}
_EQUIVALENTS: Dict[str, dict] = {}

def load_curriculums():
    global _CURRICULUMS
    if _CURRICULUMS:
        return _CURRICULUMS

    for cohort in ["K67", "K68", "K69", "K70"]:
        file_path = os.path.join(DATA_DIR, f"curriculum_{cohort.lower()}.yaml")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                _CURRICULUMS[cohort] = yaml.safe_load(f)
    return _CURRICULUMS

def load_equivalents():
    global _EQUIVALENTS
    if _EQUIVALENTS:
        return _EQUIVALENTS

    for cohort in ["K68", "K69"]:
        file_path = os.path.join(DATA_DIR, f"equivalents_{cohort.lower()}.yaml")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                _EQUIVALENTS[cohort] = yaml.safe_load(f)
    return _EQUIVALENTS

def get_curriculum_courses(cohort: str, semester: Optional[int] = None, search_term: Optional[str] = None) -> List[dict]:
    """
    Tra cứu tiến trình đào tạo của khóa (K67, K68, K69, K70).
    Lọc theo học kỳ (semester) hoặc từ khóa tìm kiếm (search_term: tên hoặc mã môn).
    """
    curriculums = load_curriculums()
    cohort_upper = cohort.strip().upper()
    if cohort_upper not in curriculums:
        available = list(curriculums.keys())
        return [{"error": f"Không có dữ liệu cho khóa {cohort}. Các khóa hiện có: {available}"}]

    curr_data = curriculums[cohort_upper]
    courses_dict = curr_data.get("courses", {})
    elective_rules = curr_data.get("elective_rules", {})
    thesis_sub = elective_rules.get("thesis_substitution", {})
    spec_groups = elective_rules.get("specializations", {}).get("groups", {})
    req_by_sem = elective_rules.get("required_by_semester", {})

    # Map mã môn sang nhóm chuyên sâu (nếu có)
    course_to_spec = {}
    for g_key, g_info in spec_groups.items():
        g_name = g_info.get("name", g_key)
        for c_code in g_info.get("courses", []):
            course_to_spec[c_code] = g_name

    # Xác định học kỳ hoặc danh sách môn tự chọn thay thế KLTN
    thesis_sub_sem = thesis_sub.get("semester", 8)
    thesis_sub_list = set(thesis_sub.get("substitution_courses", []))
    thesis_sub_condition = thesis_sub.get(
        "condition",
        "Chỉ được học để thay thế trong trường hợp trượt Khóa luận tốt nghiệp, bình thường không được học."
    )

    results = []
    search_lower = search_term.strip().lower() if search_term else None

    for code, info in courses_dict.items():
        if semester is not None and info.get("semester") != semester:
            continue

        if search_lower:
            name = info.get("name", "").lower()
            if search_lower not in code.lower() and search_lower not in name:
                continue

        c_sem = info.get("semester")
        c_type = info.get("type")

        item = {
            "code": code,
            "name": info.get("name"),
            "credits": info.get("credits"),
            "theory_credits": info.get("theory_credits"),
            "practice_credits": info.get("practice_credits"),
            "semester": c_sem,
            "type": c_type,
            "prerequisites": info.get("prerequisites", [])
        }
        if "track" in info:
            item["track"] = info["track"]
        if code in course_to_spec:
            item["specialization_group"] = course_to_spec[code]

        # Phân biệt rõ môn tự chọn thay thế KLTN (Học kỳ 8) và môn tự chọn thường (Học kỳ 1-7)
        if c_type == "elective" and (c_sem == thesis_sub_sem or code in thesis_sub_list):
            item["category"] = "Học phần tự chọn thay thế Khóa luận tốt nghiệp"
            item["note"] = (
                f"Học phần tự chọn thay thế Khóa luận tốt nghiệp (Học kỳ {c_sem}). "
                f"{thesis_sub_condition} "
                f"TUYỆT ĐỐI KHÔNG được học môn này để thay thế cho các môn tự chọn thông thường ở các học kỳ 1-7."
            )
        elif c_type == "elective":
            item["category"] = "Học phần tự chọn thông thường"
            c_credits = info.get("credits")
            item["note"] = (
                f"Học phần tự chọn thông thường (dự kiến học kỳ {c_sem}, {c_credits} tín chỉ). "
                f"Nếu bị điểm F (trượt), sinh viên có thể học lại chính môn này HOẶC học đổi sang BẤT KỲ môn tự chọn thông thường nào khác (chưa từng học) từ học kỳ 1 đến học kỳ 7 (không bắt buộc phải cùng học kỳ {c_sem}), nhưng BẮT BUỘC phải có CÙNG SỐ TÍN CHỈ ({c_credits} tín chỉ) và tuyệt đối không được lấy môn tự chọn thay thế KLTN ở học kỳ 8."
            )
        elif c_type == "compulsory":
            item["category"] = "Học phần bắt buộc"
        elif c_type == "conditional":
            item["category"] = "Học phần điều kiện"

        results.append(item)

    # Sort by semester then code
    results.sort(key=lambda x: (x.get("semester", 0), x.get("code", "")))
    return results

def lookup_equivalent_courses(cohort: str, query: str) -> List[dict]:
    """
    Tra cứu học phần tương đương và thay thế cho sinh viên K68 hoặc K69.
    query: mã học phần hoặc tên môn học (cũ hoặc mới).
    """
    equivalents_data = load_equivalents()
    cohort_upper = cohort.strip().upper()
    if cohort_upper not in equivalents_data:
        available = list(equivalents_data.keys())
        return [{"error": f"Không có bảng tương đương cho khóa {cohort}. Các khóa có dữ liệu: {available}"}]

    rules = equivalents_data[cohort_upper].get("equivalents", [])
    q_lower = query.strip().lower()
    matches = []

    for rule in rules:
        target = rule.get("target_course", {})
        source = rule.get("source_course", {})

        target_code = target.get("code", "").lower()
        target_name = target.get("name", "").lower()
        source_code = source.get("code", "").lower()
        source_name = source.get("name", "").lower()

        if (q_lower in target_code or q_lower in target_name or
            q_lower in source_code or q_lower in source_name):
            matches.append(rule)

    return matches

