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
    res = []
    for p in parts:
        p = p.strip()
        if p and len(p) >= 5 and p.isalnum():
            res.append(p)
    return res

def parse_markdown_to_curriculum(md_path: str, output_yaml_path: str):
    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    current_track = None
    current_sem = 1
    courses = {}

    for line in lines:
        line_str = line.strip()
        if not line_str.startswith("|"):
            continue

        if "Hướng chuyên sâu Công nghệ phần mềm" in line_str:
            current_track = "Công nghệ phần mềm"
            continue
        elif "Hướng chuyên sâu Mạng và hệ thống thông tin" in line_str:
            current_track = "Mạng và hệ thống thông tin"
            continue
        elif "Hướng chuyên sâu Khoa học máy tính" in line_str:
            current_track = "Khoa học máy tính"
            continue

        parts = [p.strip() for p in line_str.split("|")]
        if len(parts) < 12:
            continue

        col_sem = parts[2]
        col_name = parts[4]
        col_name_en = parts[5] if len(parts) > 5 else ""
        col_code = parts[6] if len(parts) > 6 else ""
        col_credits = parts[7] if len(parts) > 7 else ""
        col_lt = parts[8] if len(parts) > 8 else ""
        col_th = parts[9] if len(parts) > 9 else ""
        col_prereq_code = parts[11] if len(parts) > 11 else ""
        col_type = parts[12] if len(parts) > 12 else ""

        if col_code in ["Mã học phần", "---", ""]:
            continue

        course_code = clean_code(col_code)
        if not course_code or not course_code.isalnum() or len(course_code) < 4:
            continue

        try:
            sem = int(col_sem)
            current_sem = sem
        except ValueError:
            sem = current_sem

        try:
            credits = int(float(col_credits))
        except ValueError:
            try:
                credits = int(re.search(r"\d+", col_credits).group())
            except Exception:
                credits = 0

        try:
            lt = float(col_lt)
        except ValueError:
            lt = 0.0
        try:
            th = float(col_th)
        except ValueError:
            th = 0.0

        is_compulsory = "BB" in col_type
        course_type = "compulsory" if is_compulsory else "elective"
        if "PC" in col_type:
            course_type = "conditional"

        prereqs = parse_prerequisites(col_prereq_code)
        clean_name = re.sub(r"<[^>]+>", "", col_name).strip()
        clean_name_en = re.sub(r"<[^>]+>", "", col_name_en).strip()

        courses[course_code] = {
            "name": clean_name,
            "name_en": clean_name_en,
            "credits": credits,
            "theory_credits": lt,
            "practice_credits": th,
            "semester": sem,
            "type": course_type,
            "prerequisites": prereqs
        }
        if current_track and course_type == "elective":
            courses[course_code]["track"] = current_track

    data = {
        "cohort": "K68",
        "major": "Công nghệ thông tin",
        "faculty": "Khoa Công nghệ thông tin",
        "total_compulsory_credits": 109,
        "total_elective_credits": 17,
        "total_credits_required": 126,
        "courses": courses
    }

    os.makedirs(os.path.dirname(output_yaml_path), exist_ok=True)
    with open(output_yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    print(f"Successfully wrote {len(courses)} courses to {output_yaml_path}")

if __name__ == "__main__":
    md_file = r"test_parsed\k68_full\Khoa-CNTT_Danh-muc-CTDT-Khoa-68.md"
    out_yaml = r"c:\Users\HA ANH\Documents\KLTN\KLTN\data\curriculum_k68.yaml"
    parse_markdown_to_curriculum(md_file, out_yaml)
