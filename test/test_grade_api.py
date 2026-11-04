import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def test_get_student_grades_endpoint():
    response = client.get("/api/student/grades")
    assert response.status_code == 200
    data = response.json()
    assert data["student_id"] == "671234"
    assert "student_name" in data
    assert "in_progress_courses" in data
    assert "completed_courses" in data
    assert "failed_courses" in data
    assert data["accumulated_credits"] > 0
    assert data["cumulative_gpa_4"] > 0.0


def test_target_score_endpoint():
    # Môn TH02001 (Cơ sở dữ liệu) của sinh viên 671234
    payload = {
        "course_code": "TH02001",
        "target_letter": "A"
    }
    response = client.post("/api/student/target-score", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["course_code"] == "TH02001"
    assert "targets" in data
    assert data["final_exam_weight"] == 0.6
    assert data["specific_target"] is not None
    assert data["specific_target"]["letter"] == "A"
    assert data["specific_target"]["required_final_score"] > 0


def test_target_score_unregistered_course():
    payload = {
        "course_code": "UNKNOWN_COURSE_999",
        "target_letter": "A"
    }
    response = client.post("/api/student/target-score", json=payload)
    assert response.status_code == 404


def test_academic_warning_endpoint():
    response = client.get("/api/student/academic-warning")
    assert response.status_code == 200
    data = response.json()
    assert data["student_id"] == "671234"
    assert "warnings" in data
    assert "is_safe" in data


def test_get_teacher_classes_endpoint():
    response = client.get("/api/teacher/classes")
    assert response.status_code == 200
    data = response.json()
    assert data["teacher_id"] == "GV001"
    assert data["total_classes"] >= 1
    assert any(c["class_code"] == "TH02001_01" for c in data["classes"])


def test_get_class_gradebook_endpoint():
    response = client.get("/api/teacher/classes/TH02001_01/grades")
    assert response.status_code == 200
    data = response.json()
    assert data["class_code"] == "TH02001_01"
    assert data["total_students"] >= 2
    assert any(g["student_id"] == "671234" for g in data["grades"])


def test_update_grade_endpoint():
    # Giảng viên chấm điểm giữa kỳ TP2 cho sinh viên 680001 môn TH02001
    payload = {
        "student_id": "680001",
        "course_code": "TH02001",
        "class_code": "TH02001_01",
        "component_key": "tp2",
        "score": 8.5
    }
    response = client.post("/api/teacher/grades/update", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    updated_record = data["data"]
    assert updated_record["components"]["tp2"]["score"] == 8.5


def test_get_class_statistics_endpoint():
    response = client.get("/api/teacher/classes/TH02001_01/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["class_code"] == "TH02001_01"
    assert data["total_students"] >= 2
    assert "letter_distribution" in data
    assert "at_risk_students" in data
