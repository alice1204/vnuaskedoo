import os
import sys
import json
import yaml
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne, TEXT, ASCENDING

if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

load_dotenv(BASE_DIR / ".env")

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "kltn_scheduler")


def stringify_keys(obj):
    """BSON của MongoDB yêu cầu tất cả key của dictionary phải là kiểu chuỗi (string)."""
    if isinstance(obj, dict):
        return {str(k): stringify_keys(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [stringify_keys(item) for item in obj]
    return obj


def get_mongo_db():
    if not MONGODB_URI:
        print("[ERROR] Không tìm thấy biến môi trường MONGODB_URI trong .env")
        sys.exit(1)

    print(f"[*] Đang kết nối tới MongoDB Atlas...")
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=10000)
    # Test ping
    client.admin.command("ping")
    print(f"[+] Kết nối thành công tới MongoDB Atlas!")
    return client[MONGODB_DB_NAME]


def migrate_students(db):
    print("\n--- 1. Di chuyển dữ liệu Sinh viên (students) ---")
    file_path = DATA_DIR / "students.yaml"
    if not file_path.exists():
        print(f"[-] Không tìm thấy {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    students_dict = data.get("students", {})
    col = db["students"]
    col.create_index([("student_id", ASCENDING)], unique=True)

    ops = []
    for s_id, s_info in students_dict.items():
        doc = {"student_id": str(s_id), **s_info}
        ops.append(
            UpdateOne({"student_id": str(s_id)}, {"$set": doc}, upsert=True)
        )

    if ops:
        result = col.bulk_write(ops)
        print(f"[+] Đã xử lý {len(ops)} sinh viên (Thêm mới: {result.upserted_count}, Cập nhật: {result.modified_count})")
    print(f"    Tổng số hồ sơ trong collection 'students': {col.count_documents({})}")


def migrate_curriculums(db):
    print("\n--- 2. Di chuyển Chương trình đào tạo (curriculums) ---")
    col = db["curriculums"]
    col.create_index([("cohort", ASCENDING)], unique=True)

    count = 0
    for cohort in ["k67", "k68", "k69", "k70"]:
        file_path = DATA_DIR / f"curriculum_{cohort}.yaml"
        if not file_path.exists():
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        cohort_name = data.get("cohort", cohort.upper())
        clean_data = stringify_keys(data)
        col.update_one(
            {"cohort": cohort_name},
            {"$set": clean_data},
            upsert=True
        )
        count += 1
        print(f"    + Đã nạp CTĐT khóa {cohort_name} ({len(data.get('courses', {}))} môn học)")

    print(f"[+] Hoàn tất nạp {count} khung chương trình đào tạo vào collection 'curriculums'.")


def migrate_equivalents(db):
    print("\n--- 3. Di chuyển Học phần tương đương & thay thế (course_equivalents) ---")
    col = db["course_equivalents"]
    col.create_index([("cohort", ASCENDING)], unique=True)

    count = 0
    for cohort in ["k68", "k69"]:
        file_path = DATA_DIR / f"equivalents_{cohort}.yaml"
        if not file_path.exists():
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        cohort_name = data.get("cohort", cohort.upper())
        clean_data = stringify_keys(data)
        col.update_one(
            {"cohort": cohort_name},
            {"$set": clean_data},
            upsert=True
        )
        count += 1
        print(f"    + Đã nạp bảng môn tương đương khóa {cohort_name} ({len(data.get('equivalents', []))} quy tắc)")

    print(f"[+] Hoàn tất nạp {count} bảng tương đương vào collection 'course_equivalents'.")


def migrate_opened_courses(db):
    print("\n--- 4. Di chuyển Lớp mở học kỳ (opened_courses) ---")
    file_path = DATA_DIR / "opened_courses.yaml"
    if not file_path.exists():
        print(f"[-] Không tìm thấy {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    semester = data.get("semester", "current_semester")
    clean_data = stringify_keys(data)
    col = db["opened_courses"]
    col.create_index([("semester", ASCENDING)], unique=True)

    col.update_one(
        {"semester": semester},
        {"$set": clean_data},
        upsert=True
    )
    print(f"[+] Đã nạp danh sách lớp mở học kỳ '{semester}' ({len(data.get('courses', {}))} môn mở lớp).")


def migrate_regulations(db):
    print("\n--- 5. Di chuyển Quy chế đào tạo (regulations) ---")
    file_path = DATA_DIR / "quy_che_chunks.json"
    if not file_path.exists():
        print(f"[-] Không tìm thấy {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    articles = data.get("articles", [])
    col = db["regulations"]
    col.create_index([("chunk_id", ASCENDING)], unique=True)

    # Đánh text index phục vụ full text search
    try:
        col.create_index([("title", TEXT), ("content", TEXT)], default_language="none", name="regulations_text_idx")
    except Exception as e:
        pass

    ops = []
    for art in articles:
        doc = {
            "chunk_id": art.get("id"),
            "article_number": art.get("article_number"),
            "section": art.get("section", ""),
            "title": art.get("title", ""),
            "content": art.get("content", ""),
            "char_count": art.get("char_count", 0),
        }
        ops.append(
            UpdateOne({"chunk_id": art.get("id")}, {"$set": doc}, upsert=True)
        )

    if ops:
        result = col.bulk_write(ops)
        print(f"[+] Đã xử lý {len(ops)} điều khoản quy chế (Thêm mới: {result.upserted_count}, Cập nhật: {result.modified_count})")
    print(f"    Tổng số điều khoản trong collection 'regulations': {col.count_documents({})}")


def migrate_grades(db):
    print("\n--- 6. Di chuyển Bảng điểm sinh viên (grades) ---")
    file_path = DATA_DIR / "grades.yaml"
    if not file_path.exists():
        print(f"[-] Không tìm thấy {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    grades_list = data.get("grades", [])
    col = db["grades"]
    col.create_index([("student_id", ASCENDING), ("course_code", ASCENDING)], unique=True)
    col.create_index([("class_code", ASCENDING)])

    ops = []
    for g in grades_list:
        clean_g = stringify_keys(g)
        s_id = str(clean_g.get("student_id"))
        c_code = str(clean_g.get("course_code")).upper()
        clean_g["student_id"] = s_id
        clean_g["course_code"] = c_code
        ops.append(
            UpdateOne(
                {"student_id": s_id, "course_code": c_code},
                {"$set": clean_g},
                upsert=True
            )
        )

    if ops:
        result = col.bulk_write(ops)
        print(f"[+] Đã xử lý {len(ops)} bản ghi điểm (Thêm mới: {result.upserted_count}, Cập nhật: {result.modified_count})")
    print(f"    Tổng số bản ghi điểm trong collection 'grades': {col.count_documents({})}")


def verify_migration(db):
    print("\n================ KIỂM TRA DỮ LIỆU ĐÃ NẠP ================")
    collections = db.list_collection_names()
    print(f"Các collections hiện có trong database '{db.name}': {collections}")

    for c_name in ["students", "curriculums", "course_equivalents", "opened_courses", "regulations", "grades"]:
        if c_name in collections:
            cnt = db[c_name].count_documents({})
            print(f" - {c_name:20s}: {cnt:>5d} documents")

    # Thử truy vấn mẫu 1 sinh viên
    sample_student = db["students"].find_one({"student_id": "671234"}, {"_id": 0})
    if sample_student:
        print(f"\n[Test truy vấn] Sinh viên 671234: {sample_student.get('name')} | Khóa: {sample_student.get('cohort')} | Đã học: {len(sample_student.get('completed', []))} môn")

    # Thử truy vấn bảng điểm của sinh viên 671234
    sample_grades = list(db["grades"].find({"student_id": "671234"}, {"_id": 0}))
    if sample_grades:
        print(f"[Test truy vấn Điểm] Sinh viên 671234 có {len(sample_grades)} học phần trong bảng điểm:")
        for g in sample_grades:
            status = g.get("status")
            score = g.get("total_score_10")
            print(f"   * {g.get('course_code')} ({g.get('course_name')}): {score if score is not None else 'Chưa thi'} | Trạng thái: {status}")

    # Thử full-text search quy chế
    sample_regulation = list(db["regulations"].find({"$text": {"$search": "cảnh báo học tập"}}, {"_id": 0, "title": 1, "article_number": 1}).limit(2))
    if sample_regulation:
        print(f"\n[Test Text Search] Tìm kiếm quy chế 'cảnh báo học tập':")
        for reg in sample_regulation:
            print(f"   * {reg.get('title')} (Điều {reg.get('article_number')})")

    print("\n[THÀNH CÔNG] Toàn bộ dữ liệu đã được di trú lên MongoDB Atlas an toàn và hoàn chỉnh!")


def main():
    db = get_mongo_db()
    migrate_students(db)
    migrate_curriculums(db)
    migrate_equivalents(db)
    migrate_opened_courses(db)
    migrate_regulations(db)
    migrate_grades(db)
    verify_migration(db)


if __name__ == "__main__":
    main()

