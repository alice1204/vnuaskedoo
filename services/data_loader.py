from pathlib import Path
from typing import Optional
import yaml

from services.database import get_collection

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def load_yaml(filename: str):
    path = DATA_DIR / filename
    with open(path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def load_students():
    """
    Nạp danh sách sinh viên.
    Ưu tiên lấy từ MongoDB collection 'students', fallback sang students.yaml.
    """
    col = get_collection("students")
    if col is not None:
        try:
            docs = list(col.find({}, {"_id": 0}))
            if docs:
                return {"students": {doc["student_id"]: doc for doc in docs}}
        except Exception:
            pass

    return load_yaml("students.yaml")


def load_curriculum(cohort: str = "K68"):
    """
    Nạp khung chương trình đào tạo của một khóa (ví dụ 'K68').
    Ưu tiên lấy từ MongoDB collection 'curriculums', fallback sang curriculum_{cohort}.yaml.
    """
    col = get_collection("curriculums")
    cohort_upper = cohort.strip().upper()

    if col is not None:
        try:
            doc = col.find_one({"cohort": cohort_upper}, {"_id": 0})
            if doc:
                return doc
        except Exception:
            pass

    filename = f"curriculum_{cohort.lower()}.yaml"
    return load_yaml(filename)


def load_opened_courses(semester: Optional[str] = None):
    """
    Nạp danh sách các lớp mở trong học kỳ.
    Ưu tiên lấy từ MongoDB collection 'opened_courses', fallback sang opened_courses.yaml.
    """
    col = get_collection("opened_courses")
    if col is not None:
        try:
            filter_query = {"semester": semester} if semester else {}
            doc = col.find_one(filter_query, {"_id": 0})
            if doc:
                return doc
        except Exception:
            pass

    return load_yaml("opened_courses.yaml")


def load_grades(student_id: Optional[str] = None):
    """
    Nạp danh sách điểm của sinh viên.
    Ưu tiên lấy từ MongoDB collection 'grades', fallback sang data/grades.yaml.
    Nếu có student_id, lọc theo student_id đó.
    """
    col = get_collection("grades")
    if col is not None:
        try:
            filter_query = {"student_id": str(student_id)} if student_id else {}
            docs = list(col.find(filter_query, {"_id": 0}))
            if docs:
                return docs
        except Exception:
            pass

    data = load_yaml("grades.yaml")
    all_grades = data.get("grades", []) if isinstance(data, dict) else []

    if student_id:
        return [g for g in all_grades if str(g.get("student_id")) == str(student_id)]
    return all_grades


def load_class_grades(class_code: str):
    """
    Nạp danh sách điểm của toàn bộ sinh viên trong một lớp học phần (phục vụ Giảng viên).
    Ưu tiên lấy từ MongoDB collection 'grades', fallback sang data/grades.yaml.
    """
    col = get_collection("grades")
    if col is not None:
        try:
            docs = list(col.find({"class_code": class_code}, {"_id": 0}))
            if docs:
                return docs
        except Exception:
            pass

    data = load_yaml("grades.yaml")
    all_grades = data.get("grades", []) if isinstance(data, dict) else []
    return [g for g in all_grades if g.get("class_code") == class_code]


def update_grade_component(
    student_id: str,
    course_code: str,
    component_key: str,
    new_score: float,
    class_code: Optional[str] = None
) -> dict:
    """
    Cập nhật điểm một thành phần (tp1, tp2, tp3) cho sinh viên,
    tự động tính toán lại điểm tổng kết hệ 10, điểm hệ 4, điểm chữ và trạng thái.
    """
    from services.grade_calculator import calculate_course_grade

    student_id_str = str(student_id)
    course_code_str = str(course_code).upper()

    col = get_collection("grades")
    if col is not None:
        try:
            doc = col.find_one({"student_id": student_id_str, "course_code": course_code_str})
            if doc:
                components = doc.get("components", {})
                if component_key in components:
                    components[component_key]["score"] = new_score
                else:
                    components[component_key] = {"name": component_key.upper(), "weight": 0.3, "score": new_score}

                recalculated = calculate_course_grade(components)
                update_fields = {
                    f"components.{component_key}.score": new_score,
                    "total_score_10": recalculated["total_score_10"],
                    "gpa_4": recalculated["gpa_4"],
                    "letter_grade": recalculated["letter_grade"],
                    "status": recalculated["status"],
                }
                col.update_one(
                    {"student_id": student_id_str, "course_code": course_code_str},
                    {"$set": update_fields}
                )
                doc.update(update_fields)
                doc["components"] = components
                doc.pop("_id", None)
                return doc
        except Exception:
            pass

    # Fallback cập nhật file data/grades.yaml
    path = DATA_DIR / "grades.yaml"
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    grades_list = data.get("grades", [])
    target = None
    for item in grades_list:
        if str(item.get("student_id")) == student_id_str and str(item.get("course_code")).upper() == course_code_str:
            target = item
            break

    if target is None:
        raise ValueError(f"Không tìm thấy học phần {course_code} của sinh viên {student_id}")

    components = target.get("components", {})
    if component_key in components:
        components[component_key]["score"] = new_score
    else:
        components[component_key] = {"name": component_key.upper(), "weight": 0.3, "score": new_score}

    recalculated = calculate_course_grade(components)
    target["components"] = components
    target["total_score_10"] = recalculated["total_score_10"]
    target["gpa_4"] = recalculated["gpa_4"]
    target["letter_grade"] = recalculated["letter_grade"]
    target["status"] = recalculated["status"]

    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)

    return target


def get_student_grades_summary(student_id: str) -> dict:
    """
    Tổng hợp bảng điểm của sinh viên bao gồm:
    - Môn đang học (in_progress)
    - Môn đã hoàn thành (passed)
    - Môn đã trượt (failed)
    - Tổng tín chỉ tích lũy, GPA hệ 4 và GPA hệ 10
    """
    from services.grade_calculator import calculate_gpa

    student_id_str = str(student_id)
    student_grades = load_grades(student_id_str)

    in_progress = []
    completed = []
    failed = []

    for item in student_grades:
        st = item.get("status")
        if st == "in_progress":
            in_progress.append(item)
        elif st == "passed":
            completed.append(item)
        elif st == "failed":
            failed.append(item)

    gpa_info = calculate_gpa(student_grades)

    return {
        "student_id": student_id_str,
        "accumulated_credits": gpa_info["total_credits"],
        "passed_credits": gpa_info["passed_credits"],
        "cumulative_gpa_4": gpa_info["gpa_4"],
        "cumulative_gpa_10": gpa_info["gpa_10"],
        "in_progress_courses": in_progress,
        "completed_courses": completed,
        "failed_courses": failed,
    }