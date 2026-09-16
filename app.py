from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
)

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from models.schemas import (
    ExplainScheduleRequest,
    ScheduleRequest,
    ChatMessageRequest,
    ChatResponse,
)

from services.academic_rules import (
    get_candidate_courses,
    get_student,
)

from services.scheduler import (
    create_schedule,
)

from services.ai_service import (
    explain_schedule,
    explain_schedule_stream,
)

from services.agent_service import (
    chat_agent,
    chat_agent_stream,
)

from services.student_service import (
    get_current_student_id,
)


app = FastAPI(
    title="Student Scheduler API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/ui", StaticFiles(directory="frontend", html=True), name="ui")

@app.get("/")
def root():
    return {
        "message":
            "Student Scheduler API is running"
    }


@app.get("/me")
def get_me(
    student_id: str = Depends(
        get_current_student_id
    ),
):
    student = get_student(
        student_id
    )

    if student is None:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy hồ sơ sinh viên.",
        )

    return {
        "student_id": student_id,
        "name": student.get("name"),
        "major": student.get("major"),
        "current_semester":
            student.get("current_semester"),
    }


@app.post("/schedule")
def generate_schedule(
    request: ScheduleRequest,

    student_id: str = Depends(
        get_current_student_id
    ),
):
    try:
        candidates = get_candidate_courses(
            student_id=student_id,
            allow_early=request.allow_early,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )

    result = create_schedule(
        candidates=candidates,
        target_credits=
            request.target_credits,
    )

    return result


@app.post("/schedule/explain")
def explain_generated_schedule(
    request: ExplainScheduleRequest,
):
    explanation = explain_schedule(
        request.schedule_result
    )

    return {
        "explanation": explanation
    }


@app.post("/schedule/explain-stream")
def explain_generated_schedule_stream(
    request: ExplainScheduleRequest,
):
    return StreamingResponse(
        explain_schedule_stream(
            request.schedule_result
        ),
        media_type="text/plain; charset=utf-8",
    )


@app.post("/chat", response_model=ChatResponse)
def handle_chat(request: ChatMessageRequest):
    response_text = chat_agent(
        message=request.message,
        session_id=request.session_id or "default_session",
    )
    return {
        "response": response_text,
        "session_id": request.session_id or "default_session",
        "tools_called": [],
    }


@app.post("/chat/stream")
def handle_chat_stream(request: ChatMessageRequest):
    return StreamingResponse(
        chat_agent_stream(
            message=request.message,
            session_id=request.session_id or "default_session",
        ),
        media_type="text/plain; charset=utf-8",
    )