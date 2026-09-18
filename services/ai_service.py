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
    "gemini-3.5-flash-lite",
)


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
Bạn là trợ lý học vụ. Hãy viết một đoạn nhận xét ngắn gọn (dưới 150 từ), giọng điệu thân thiện dành cho sinh viên về thời khóa biểu kỳ này dựa trên dữ liệu sau:

{summary_text}

Lưu ý: Nêu rõ môn nào được ưu tiên học lại, môn nào đúng tiến độ hoặc học trước. Trả lời bằng tiếng Việt.
"""

def explain_schedule(schedule_result: dict):
    prompt = _build_prompt(schedule_result)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level="minimal")
        )
    )
    return response.text

def explain_schedule_stream(schedule_result: dict):
    prompt = _build_prompt(schedule_result)
    response_stream = client.models.generate_content_stream(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level="minimal")
        )
    )
    for chunk in response_stream:
        if chunk.text:
            yield chunk.text