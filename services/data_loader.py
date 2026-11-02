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