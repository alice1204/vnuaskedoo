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
    # Find all standard course code patterns: 2-4 letters followed by 4-5 numbers
    matches = re.findall(r"[A-Z]{2,5}\d{4,5}", cleaned.upper())
    return list(dict.fromkeys(matches))

def parse_k69_k70_markdown(md_path: str, output_yaml_path: str, cohort: str, total_compulsory: int, total_elective: int, total_required: int):
    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    current_sem = 1
    current_track = None
    courses = {}

    for line in lines:
        line_str = line.strip()
        if not line_str.startswith("|"):
            continue

        if "Hướng chuyên sâu Công nghệ phần mềm" in line_str:
            current_track = "Công nghệ phần mềm"
            continue
        elif "Hướng chuyên sâu Mạng và Hệ thống thông tin" in line_str:
            current_track = "Mạng và Hệ thống thông tin"
            continue
        elif "Hướng chuyên sâu Khoa học máy tính" in line_str:
            current_track = "Khoa học máy tính"
            continue

        parts = [p.strip() for p in line_str.split("|")]
        if len(parts) < 8:
            continue

        col_sem = parts[1]
        col_code = parts[2]
        col_name = parts[3]
        col_credits = parts[4]
        col_lt = parts[5] if len(parts) > 5 else ""
        col_th = parts[6] if len(parts) > 6 else ""
        col_type = parts[7] if len(parts) > 7 else ""
        col_prereq = parts[-2] if len(parts) >= 9 else ""

        if col_code in ["Mã học phần", "---", ""] or "Mã học" in col_code or "Tổng số" in col_code:
            continue

        course_code = clean_code(col_code)
        if not re.match(r"^[A-Z]{2,5}\d{4,5}$", course_code.upper()):
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

        if "Khóa luận tốt nghiệp" in clean_name or "Khoá luận tốt nghiệp" in clean_name:
            course_type = "compulsory"

        prereqs = parse_prerequisites(col_prereq)

        try:
            lt_val = float(col_lt.replace(",", "."))
        except Exception:
            lt_val = 0.0

        try:
            th_val = float(col_th.replace(",", "."))
        except Exception:
            th_val = 0.0

        course_data = {
            "name": clean_name,
            "credits": credits,
            "theory_credits": lt_val,
            "practice_credits": th_val,
            "semester": current_sem,
            "type": course_type,
            "prerequisites": prereqs
        }

        if current_track and (current_sem in [6, 7]):
            course_data["track"] = current_track

        courses[course_code] = course_data

    data = {
        "cohort": cohort,
        "major": "Công nghệ thông tin",
        "faculty": "Khoa Công nghệ thông tin",
        "total_compulsory_credits": total_compulsory,
        "total_elective_credits": total_elective,
        "total_credits_required": total_required,
        "courses": courses
    }

    os.makedirs(os.path.dirname(output_yaml_path), exist_ok=True)
    with open(output_yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    print(f"Successfully created {cohort} at {output_yaml_path} with {len(courses)} courses!")

if __name__ == "__main__":
    k69_md = r"test_parsed\k69_full_kehoach\Khoa-CNTT_Danh-muc-CTDT-Khoa-69.md"
    out_k69 = r"data\curriculum_k69.yaml"
    parse_k69_k70_markdown(k69_md, out_k69, "K69", 134, 6, 140)

    k70_md = r"test_parsed\k70_sample\Khoa-CNTT_Danh-muc-CTDT-Khoa-70.md"
    out_k70 = r"data\curriculum_k70.yaml"
    parse_k69_k70_markdown(k70_md, out_k70, "K70", 134, 6, 140)
