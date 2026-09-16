import os
import re
import yaml

def clean_code(val: str) -> str:
    if not val:
        return ""
    cleaned = re.sub(r"<[^>]+>", "", val).strip()
    return cleaned.replace(" ", "").replace("\n", "")

def parse_prerequisites(val: str) -> list[str]:
    cleaned = clean_code(val)
    if not cleaned or cleaned in ["-", "None", "không", "null"]:
        return []
    parts = re.split(r"[,;/]+", cleaned)
    return [p.strip() for p in parts if p.strip() and len(p.strip()) >= 5 and p.strip().isalnum()]

def build_curriculum_k67(md_path: str, output_yaml_path: str):
    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    current_sem = 1
    courses = {}

    for line in lines:
        line_str = line.strip()
        if not line_str.startswith("|"):
            continue

        parts = [p.strip() for p in line_str.split("|")]
        if len(parts) < 11:
            continue

        col_sem = parts[1]
        col_name = parts[3]
        col_code = parts[4]
        col_credits = parts[5]
        col_lt = parts[6] if len(parts) > 6 else ""
        col_th = parts[7] if len(parts) > 7 else ""
        col_prereq_code = parts[9] if len(parts) > 9 else ""
        col_type = parts[11] if len(parts) > 11 else ""

        if col_code in ["Mã học phần", "---", ""] or "Mã học" in col_code:
            continue

        course_code = clean_code(col_code)
        if not course_code or not course_code.isalnum() or len(course_code) < 4:
            continue

        try:
            current_sem = int(col_sem)
        except ValueError:
            pass

        try:
            credits = int(float(col_credits.replace(",", ".")))
        except ValueError:
            try:
                credits = int(re.search(r"\d+", col_credits).group())
            except Exception:
                credits = 0

        course_type = "compulsory" if "BB" in col_type else "elective"
        if "PC" in col_type:
            course_type = "conditional"

        clean_name = re.sub(r"<[^>]+>", "", col_name).strip()

        courses[course_code] = {
            "name": clean_name,
            "credits": credits,
            "theory_credits": float(col_lt.replace(",", ".")) if col_lt.replace(",", ".").replace(".", "").isdigit() else 0.0,
            "practice_credits": float(col_th.replace(",", ".")) if col_th.replace(",", ".").replace(".", "").isdigit() else 0.0,
            "semester": current_sem,
            "type": course_type,
            "prerequisites": parse_prerequisites(col_prereq_code)
        }

    data = {
        "cohort": "K67",
        "major": "Công nghệ thông tin",
        "faculty": "Khoa Công nghệ thông tin",
        "total_compulsory_credits": 119,
        "total_elective_credits": 12,
        "total_credits_required": 131,
        "courses": courses
    }

    os.makedirs(os.path.dirname(output_yaml_path), exist_ok=True)
    with open(output_yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    print(f"K67 Curriculum: Successfully created {output_yaml_path} with {len(courses)} courses!")

if __name__ == "__main__":
    md_file = r"test_parsed\k67_cntt\Khoa-CNTT_Danh-muc-CTDT-Khoa-67.md"
    out_yaml = r"data\curriculum_k67.yaml"
    build_curriculum_k67(md_file, out_yaml)
