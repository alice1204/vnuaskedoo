import pytest
from fastapi.testclient import TestClient
from app import app
from services.knowledge_service import (
    get_curriculum_courses,
    lookup_equivalent_courses,
    load_curriculums,
    load_equivalents,
)
from services.regulation_service import search_regulations, load_regulations
from services.agent_service import (
    tool_lookup_curriculum,
    tool_lookup_equivalent_course,
    tool_search_regulations,
    tool_generate_schedule,
)

client = TestClient(app)

def test_load_all_curriculums():
    curr = load_curriculums()
    assert "K67" in curr
    assert "K68" in curr
    assert "K69" in curr
    assert "K70" in curr
    assert len(curr["K67"]["courses"]) >= 60
    assert len(curr["K68"]["courses"]) >= 70
    assert len(curr["K69"]["courses"]) >= 60
    assert len(curr["K70"]["courses"]) >= 60

def test_k67_curriculum_contains_kltn():
    courses = get_curriculum_courses("K67", search_term="Khóa luận tốt nghiệp")
    assert len(courses) > 0
    kltn = courses[0]
    assert kltn["code"] == "TH04299"
    assert kltn["credits"] == 10

def test_k69_curriculum_contains_kltn():
    courses = get_curriculum_courses("K69", search_term="Khóa luận tốt nghiệp")
    assert len(courses) > 0
    kltn = courses[0]
    assert kltn["code"] == "TH94491"
    assert kltn["credits"] == 10

def test_k70_curriculum_semester_filter():
    sem4 = get_curriculum_courses("K70", semester=4)
    assert len(sem4) > 0
    for c in sem4:
        assert c["semester"] == 4

def test_equivalents_k68():
    eqs = lookup_equivalent_courses("K68", "Cấu trúc dữ liệu và giải thuật")
    assert len(eqs) > 0
    first = eqs[0]
    assert "source_course" in first
    assert "target_course" in first
    assert first["target_course"]["code"] == "TH02046"

def test_equivalents_k69():
    eqs = lookup_equivalent_courses("K69", "Xác suất thống kê")
    assert len(eqs) > 0
    first = eqs[0]
    assert first["source_course"]["code"] == "TH01007"
    assert first["target_course"]["code"] == "TH92023"

def test_search_regulations():
    regs = load_regulations()
    assert len(regs) >= 60

    results = search_regulations("cảnh báo học tập", top_k=2)
    assert len(results) > 0
    assert any("cảnh báo" in r.get("title", "").lower() or "cảnh báo" in r.get("content", "").lower() for r in results)

    art18 = search_regulations("Điều 18", top_k=1)
    assert len(art18) > 0
    assert art18[0].get("article_number") == 18

def test_tools():
    t1 = tool_lookup_curriculum("K69", semester=2)
    assert "code" in t1

    t2 = tool_lookup_equivalent_course("K68", "Cấu trúc dữ liệu")
    assert "source_course" in t2

    t3 = tool_search_regulations("điều 18")
    assert "title" in t3

    t4 = tool_generate_schedule("671234", target_credits=18)
    assert "schedule" in t4

def test_chat_stream_endpoint():
    # Test that /chat/stream accepts POST and streams content
    response = client.post(
        "/chat/stream",
        json={
            "message": "Xin chào",
            "session_id": "test_pytest_session"
        }
    )
    assert response.status_code == 200
    content = response.text
    assert len(content) > 0
