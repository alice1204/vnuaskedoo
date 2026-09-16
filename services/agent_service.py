import os
import json
import time
from typing import Dict, Generator, Optional, Any
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ClientError

from services.knowledge_service import (
    get_curriculum_courses,
    lookup_equivalent_courses,
)
from services.regulation_service import search_regulations
from services.academic_rules import get_candidate_courses
from services.scheduler import create_schedule

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

FALLBACK_MODELS = [
    GEMINI_MODEL,
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-flash-lite-latest",
]
# Remove duplicates while preserving order
FALLBACK_MODELS = list(dict.fromkeys(FALLBACK_MODELS))

client = genai.Client(api_key=GEMINI_API_KEY)

# Tool 1: Tra cứu tiến trình đào tạo K67 - K70
def tool_lookup_curriculum(cohort: str, semester: Optional[int] = None, search_term: Optional[str] = None) -> str:
    """
    Tra cứu tiến trình chương trình đào tạo của Khoa CNTT cho các khóa K67, K68, K69, K70.
    Args:
        cohort: Khóa sinh viên cần tra cứu, ví dụ 'K67', 'K68', 'K69', 'K70'.
        semester: Học kỳ dự kiến (từ 1 đến 8), có thể để None nếu muốn xem toàn khóa hoặc tìm theo tên môn.
        search_term: Tên môn học hoặc mã học phần cần tìm kiếm (ví dụ: 'Toán giải tích', 'TH02046').
    """
    results = get_curriculum_courses(cohort=cohort, semester=semester, search_term=search_term)
    if not results:
        return f"Không tìm thấy học phần nào phù hợp trong CTĐT khóa {cohort}."
    # Giới hạn thông tin gọn nhẹ để tiết kiệm token
    compact_results = []
    for r in results[:10]:
        compact_results.append({
            "code": r.get("code"),
            "name": r.get("name"),
            "credits": r.get("credits"),
            "semester": r.get("semester"),
            "type": r.get("type"),
            "prerequisites": r.get("prerequisites", [])
        })
    return json.dumps(compact_results, ensure_ascii=False)

# Tool 2: Tra cứu học phần tương đương và thay thế K68, K69
def tool_lookup_equivalent_course(cohort: str, query: str) -> str:
    """
    Tra cứu học phần tương đương hoặc học phần thay thế cho sinh viên K68 hoặc K69 của Khoa CNTT.
    Dùng khi sinh viên bị nợ môn cũ, muốn biết môn mới thay thế là môn gì hoặc ngược lại.
    Args:
        cohort: Khóa cần tra cứu ('K68' hoặc 'K69').
        query: Tên học phần hoặc mã học phần cần tra cứu (ví dụ: 'Xác suất thống kê', 'TH01007', 'TH02016').
    """
    results = lookup_equivalent_courses(cohort=cohort, query=query)
    if not results:
        return f"Không tìm thấy quy tắc học phần tương đương nào cho '{query}' trong danh mục của {cohort}."
    return json.dumps(results[:8], ensure_ascii=False)

# Tool 3: Tra cứu Quy chế đào tạo và Sổ tay sinh viên
def tool_search_regulations(query: str) -> str:
    """
    Tra cứu các điều khoản trong Quy chế đào tạo đại học và Sổ tay sinh viên của Học viện Nông nghiệp Việt Nam.
    Dùng để trả lời các câu hỏi về: điều kiện cảnh báo học tập, buộc thôi học, thang điểm, điều kiện xét tốt nghiệp,
    rút học phần, học lại, học cải thiện, nghỉ học tạm thời, điểm rèn luyện, học bổng, miễn giảm học phí.
    Args:
        query: Từ khóa hoặc câu hỏi cần tra cứu quy chế (ví dụ: 'cảnh báo học tập', 'buộc thôi học', 'thang điểm 4', 'xét tốt nghiệp').
    """
    results = search_regulations(query=query, top_k=2)
    compact_chunks = []
    for art in results:
        if "error" in art or "message" in art:
            compact_chunks.append(art)
            continue
        content = art.get("content", "")
        # Rút gọn nội dung nếu quá dài (tối đa 1200 ký tự)
        if len(content) > 1200:
            content = content[:1200] + "... [xem tiếp trong quy chế]"
        compact_chunks.append({
            "title": art.get("title"),
            "content": content
        })
    return json.dumps(compact_chunks, ensure_ascii=False)

# Tool 4: Tự động xếp thời khóa biểu dựa trên thuật toán Rule-based Scheduler
def tool_generate_schedule(student_id: str = "671234", target_credits: int = 18, allow_early: bool = True) -> str:
    """
    Tự động xếp lịch học đề xuất cho sinh viên dựa trên tình trạng học tập thực tế, các môn đã học, nợ môn và môn mở.
    Args:
        student_id: Mã sinh viên (mặc định '671234' hoặc '671235').
        target_credits: Số tín chỉ mong muốn đăng ký (từ 15 đến 25 tín chỉ).
        allow_early: Cho phép đề xuất học vượt môn kỳ tiếp theo nếu thỏa mãn điều kiện tiên quyết.
    """
    try:
        candidates = get_candidate_courses(student_id=student_id, allow_early=allow_early)
        schedule_result = create_schedule(candidates=candidates, target_credits=target_credits)
        return json.dumps(schedule_result, ensure_ascii=False)
    except Exception as e:
        return f"Không thể tạo thời khóa biểu: {str(e)}"

SYSTEM_INSTRUCTION = """
Bạn là Cố vấn Học vụ AI của Học viện Nông nghiệp Việt Nam (Khoa Công nghệ thông tin).
Nhiệm vụ của bạn là hỗ trợ sinh viên giải đáp thắc mắc về:
1. Tiến trình chương trình đào tạo của các khóa K67, K68, K69, K70.
2. Danh mục học phần tương đương và thay thế của K68 và K69.
3. Quy chế đào tạo theo tín chỉ (cảnh báo học tập, buộc thôi học, thang điểm, rút môn, xét tốt nghiệp...) và chính sách sinh viên.
4. Tự động xếp và gợi ý kế hoạch học tập/thời khóa biểu khi sinh viên yêu cầu.

NGUYÊN TẮC HOẠT ĐỘNG:
- Luôn sử dụng CÔNG CỤ (TOOLS) được cung cấp để tra cứu dữ liệu chính xác trước khi trả lời. Tuyệt đối không tự bịa đặt mã môn, số tín chỉ hoặc điều khoản quy chế.
- Trình bày câu trả lời bằng Markdown rõ ràng, thân thiện, dễ đọc:
  + Dùng BẢNG (Markdown Table) khi liệt kê môn học hoặc so sánh môn tương đương.
  + Ghi rõ nguồn trích dẫn ở cuối (Ví dụ: [Nguồn: Điều 18 - Quy chế đào tạo Học viện] hoặc [Nguồn: CTĐT K68 Khoa CNTT]).
- Nếu sinh viên yêu cầu xếp lịch hoặc gợi ý thời khóa biểu, hãy gọi tool xếp lịch và tóm tắt kết quả theo môn học lại, môn đúng tiến độ và môn học vượt.
"""

# In-memory session store (RAM)
_SESSIONS: Dict[str, Any] = {}

def create_chat_session(model_name: str):
    tools = [
        tool_lookup_curriculum,
        tool_lookup_equivalent_course,
        tool_search_regulations,
        tool_generate_schedule,
    ]
    return client.chats.create(
        model=model_name,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.2,
            tools=tools,
        ),
    )

def get_or_create_chat(session_id: str, model_name: Optional[str] = None):
    if session_id in _SESSIONS:
        return _SESSIONS[session_id]

    target_model = model_name or FALLBACK_MODELS[0]
    chat = create_chat_session(target_model)
    _SESSIONS[session_id] = chat
    return chat

def chat_agent(message: str, session_id: str = "default_session") -> str:
    for model_name in FALLBACK_MODELS:
        try:
            chat = get_or_create_chat(session_id, model_name=model_name)
            response = chat.send_message(message)
            return response.text
        except Exception as e:
            err_str = str(e)
            if any(k in err_str for k in ["429", "503", "UNAVAILABLE", "RESOURCE_EXHAUSTED"]):
                _SESSIONS.pop(session_id, None)
                continue
            return f"Lỗi xử lý: {err_str}"
    return "Hệ thống đang tiếp nhận nhiều yêu cầu cùng lúc (Rate limit). Bạn vui lòng đợi khoảng 15 giây và thử lại câu hỏi nhé!"

def chat_agent_stream(message: str, session_id: str = "default_session") -> Generator[str, None, None]:
    for model_name in FALLBACK_MODELS:
        try:
            chat = get_or_create_chat(session_id, model_name=model_name)
            response_stream = chat.send_message_stream(message)
            has_yielded = False
            for chunk in response_stream:
                try:
                    if chunk.text:
                        yield chunk.text
                        has_yielded = True
                except Exception:
                    continue
            if has_yielded:
                return
        except Exception as e:
            err_str = str(e)
            if any(k in err_str for k in ["429", "503", "UNAVAILABLE", "RESOURCE_EXHAUSTED"]):
                _SESSIONS.pop(session_id, None)
                continue
            yield f"Lỗi xử lý: {err_str}"
            return
    yield "Hệ thống đang tiếp nhận nhiều yêu cầu cùng lúc (Rate limit). Bạn vui lòng đợi khoảng 15 giây và thử lại câu hỏi nhé!"

