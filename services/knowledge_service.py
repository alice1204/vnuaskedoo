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
    results = []

    search_lower = search_term.strip().lower() if search_term else None

    for code, info in courses_dict.items():
        if semester is not None and info.get("semester") != semester:
            continue

        if search_lower:
            name = info.get("name", "").lower()
            if search_lower not in code.lower() and search_lower not in name:
                continue

        item = {
            "code": code,
            "name": info.get("name"),
            "credits": info.get("credits"),
            "theory_credits": info.get("theory_credits"),
            "practice_credits": info.get("practice_credits"),
            "semester": info.get("semester"),
            "type": info.get("type"),
            "prerequisites": info.get("prerequisites", [])
        }
        if "track" in info:
            item["track"] = info["track"]
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

