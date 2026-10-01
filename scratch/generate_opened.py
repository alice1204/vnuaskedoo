import yaml
import random

with open("data/curriculum_k68.yaml", "r", encoding="utf8") as f:
    curriculum = yaml.safe_load(f)

with open("data/students.yaml", "r", encoding="utf8") as f:
    students_data = yaml.safe_load(f)

failed_courses = students_data["students"]["680001"]["failed"]

opened = {}

days = ["T2", "T3", "T4", "T5", "T6", "T7"]
shifts = ["1-3", "4-5", "6-8", "9-10"]

courses_to_open = set(failed_courses)
for code, info in curriculum.get("courses", {}).items():
    sem = info.get("semester")
    if sem in [1, 3, 5, 7]:
        courses_to_open.add(code)
    # also open electives/conditionals so student can take them
    elif info.get("type") in ["elective", "conditional"]:
        courses_to_open.add(code)

for code in courses_to_open:
    num_classes = random.randint(1, 3)
    classes = []
    for i in range(num_classes):
        day = random.choice(days)
        shift = random.choice(shifts)
        room = str(random.randint(1, 9)) + "0" + str(random.randint(1, 9))
        classes.append({
            "id": room,
            "times": [f"{day}({shift})"]
        })
    opened[code] = {"classes": classes}

output = {
    "semester": "2026-2027-1",
    "courses": opened
}

with open("data/opened_courses.yaml", "w", encoding="utf8") as f:
    yaml.dump(output, f, allow_unicode=True, sort_keys=False)
