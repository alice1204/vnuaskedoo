import json
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()


GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY"
)

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.1-flash-lite",
)

FALLBACK_MODELS = [
    GEMINI_MODEL,
    "gemini-3.1-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-3.5-flash-lite",
]
FALLBACK_MODELS = list(dict.fromkeys(FALLBACK_MODELS))


client = genai.Client(
    api_key=GEMINI_API_KEY
)

def _build_prompt(schedule_result: dict) -> str:
    schedule = schedule_result.get("schedule", [])
    total_credits = schedule_result.get("total_credits", 0)

    retake_courses = [
        f"{item['course_name']} ({item['credits']} TC)"
        for item in schedule if item.get("reason") == "retake"
    ]
    normal_courses = [
        f"{item['course_name']} ({item['credits']} TC)"
        for item in schedule if item.get("reason") == "normal"
    ]
    early_courses = [
        f"{item['course_name']} ({item['credits']} TC)"
        for item in schedule if item.get("reason") == "early"
    ]

    summary_text = f"""
Tổng số tín chỉ đăng ký: {total_credits}
- Môn học lại: {', '.join(retake_courses) if retake_courses else 'Không có'}
- Môn đúng tiến độ: {', '.join(normal_courses) if normal_courses else 'Không có'}
- Môn học trước: {', '.join(early_courses) if early_courses else 'Không có'}
""".strip()

    return f"""
Bạn là trợ lý học vụ AI. Hãy viết một đoạn nhận xét ngắn gọn (khoảng 80-120 từ), giọng điệu thân thiện, tích cực dành cho sinh viên về thời khóa biểu kỳ này dựa trên dữ liệu sau:

{summary_text}

Lưu ý: Nêu rõ môn nào được ưu tiên học lại, môn nào đúng tiến độ hoặc học trước, và đưa ra một lời động viên ngắn. Trả lời bằng tiếng Việt.
"""

def explain_schedule(schedule_result: dict) -> str:
    prompt = _build_prompt(schedule_result)
    for model_name in FALLBACK_MODELS:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            return response.text
        except Exception as e:
            err_str = str(e)
            if any(k in err_str for k in ["429", "503", "UNAVAILABLE", "RESOURCE_EXHAUSTED"]):
                continue
            return f"Không thể tạo giải thích AI lúc này: {err_str}"
    total_credits = schedule_result.get("total_credits", 0)
    return f"Thời khóa biểu của bạn đã được xếp tối ưu với {total_credits} tín chỉ. Hiện tại AI đang bận, bạn vui lòng tham khảo bảng môn học phía trên nhé!"

def explain_schedule_stream(schedule_result: dict):
    prompt = _build_prompt(schedule_result)
    for model_name in FALLBACK_MODELS:
        try:
            response_stream = client.models.generate_content_stream(
                model=model_name,
                contents=prompt,
            )
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
                continue
            yield f"Không thể tạo giải thích AI lúc này: {err_str}"
            return

    total_credits = schedule_result.get("total_credits", 0)
    yield f"Thời khóa biểu của bạn đã được xếp tối ưu với {total_credits} tín chỉ. Hiện tại AI đang bận, bạn vui lòng tham khảo bảng môn học phía trên nhé!"