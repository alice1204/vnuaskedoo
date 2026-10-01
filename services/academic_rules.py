from services.data_loader import (
    load_students,
    load_curriculum,
    load_opened_courses,
)


def get_student(student_id: str):
    data = load_students()

    return data["students"].get(student_id)


def prerequisites_satisfied(
    course: dict,
    completed_courses: set[str]
) -> bool:

    prerequisites = course.get(
        "prerequisites",
        []
    )

    return all(
        prerequisite in completed_courses
        for prerequisite in prerequisites
    )


def get_candidate_courses(
    student_id: str,
    allow_early: bool = True
):

    student = get_student(student_id)

    if student is None:
        raise ValueError(
            f"Không tìm thấy sinh viên {student_id}"
        )

    cohort = student.get("cohort", "K68")
    curriculum = load_curriculum(cohort)["courses"]
    opened_courses = load_opened_courses()["courses"]

    completed = set(
        student.get("completed", [])
    )

    failed = set(
        student.get("failed", [])
    )

    current_semester = student["current_semester"]

    candidates = []

    for course_code, course in curriculum.items():

        # 1. Môn đã học xong -> bỏ
        if course_code in completed:
            continue

        # 2. Không có lớp mở -> bỏ
        if course_code not in opened_courses:
            continue

        # 3. Chưa đủ tiên quyết -> bỏ
        if not prerequisites_satisfied(
            course,
            completed
        ):
            continue

        course_semester = course["semester"]

        # 4. Môn từng trượt
        if course_code in failed:

            priority = 1
            reason = "retake"

        # 5. Môn đúng tiến độ
        elif course_semester == current_semester:

            priority = 2
            reason = "normal"

        # 6. Môn của kỳ tiếp theo
        elif (
            allow_early
            and course_semester == current_semester + 1
        ):

            priority = 3
            reason = "early"

        else:
            continue

        candidates.append(
            {
                "code": course_code,
                "name": course["name"],
                "credits": course["credits"],
                "priority": priority,
                "reason": reason,
                "classes":
                    opened_courses[course_code]["classes"],
            }
        )

    candidates.sort(
        key=lambda course: course["priority"]
    )

    return candidates