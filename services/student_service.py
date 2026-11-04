import os

from dotenv import load_dotenv


load_dotenv()


def get_current_student_id() -> str:
    """
    Prototype:
    Giả lập MSSV của sinh viên hiện đang đăng nhập.

    Khi tích hợp với hệ thống trường, hàm này sẽ được
    thay bằng việc lấy student_id từ session/JWT/SSO.
    """

    return os.getenv(
        "MOCK_CURRENT_STUDENT_ID",
        "671234",
    )


def get_current_teacher_id() -> str:
    """
    Prototype:
    Giả lập Mã Giảng viên hiện đang đăng nhập (ví dụ: GV001 - ThS. Nguyễn Giảng Viên).
    """
    return os.getenv(
        "MOCK_CURRENT_TEACHER_ID",
        "GV001",
    )