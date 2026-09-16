import os
import re
import yaml
import openpyxl

def build_k68_equivalents(excel_path: str, output_yaml_path: str):
    wb = openpyxl.load_workbook(excel_path)
    ws = wb.active

    equivalents = []
    # Data starts from row 6
    for row in list(ws.iter_rows(values_only=True))[5:]:
        if not row or not row[0]:
            continue
        tt, k68_code, k68_name, k68_tc, k67_code, k67_name, k67_tc = row[:7]

        if not k68_code:
            continue

        equivalents.append({
            "target_course": {
                "code": str(k68_code).strip(),
                "name": str(k68_name).strip() if k68_name else "",
                "credits": int(k68_tc) if k68_tc is not None else 0,
                "cohort": "K68"
            },
            "source_course": {
                "code": str(k67_code).strip().replace("\n", "; "),
                "name": str(k67_name).strip().replace("\n", "; ") if k67_name else "",
                "credits": int(k67_tc) if k67_tc is not None else 0,
                "cohort": "K67 về trước"
            },
            "note": "Học phần thay thế / tương đương cho sinh viên K67 về trước học cùng K68"
        })

    data = {
        "cohort": "K68",
        "reference_cohort": "K67 về trước",
        "faculty": "Khoa Công nghệ thông tin",
        "description": "Danh sách học phần tương đương với học phần Khóa 68 - Ngành Công nghệ thông tin",
        "total_rules": len(equivalents),
        "equivalents": equivalents
    }

    os.makedirs(os.path.dirname(output_yaml_path), exist_ok=True)
    with open(output_yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    print(f"K68 Equivalents: Successfully generated {len(equivalents)} rules at {output_yaml_path}")


def build_k69_equivalents(md_path: str, output_yaml_path: str):
    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    equivalents = []
    for line in lines:
        line_str = line.strip()
        if not line_str.startswith("|"):
            continue

        parts = [p.strip() for p in line_str.split("|")]
        # |STT|Mã học phần|Tên học phần|Số tín chỉ|Mã học phần tương đương|Tên học phần tương đương|Số tín chỉ|
        if len(parts) < 8:
            continue

        stt = parts[1]
        k69_code = parts[2]
        k69_name = parts[3]
        k69_credits = parts[4]
        old_code = parts[5]
        old_name = parts[6]
        old_credits = parts[7]

        if k69_code in ["Mã học phần", "---", ""]:
            continue

        try:
            c_k69 = int(float(k69_credits))
        except Exception:
            c_k69 = 0

        try:
            c_old = int(float(old_credits))
        except Exception:
            c_old = 0

        equivalents.append({
            "target_course": {
                "code": k69_code,
                "name": k69_name,
                "credits": c_k69,
                "cohort": "K69"
            },
            "source_course": {
                "code": old_code,
                "name": old_name,
                "credits": c_old,
                "cohort": "K68 về trước"
            },
            "note": "Học phần tương đương áp dụng cho Khóa 69 Khoa CNTT"
        })

    data = {
        "cohort": "K69",
        "reference_cohort": "K68 về trước",
        "faculty": "Khoa Công nghệ thông tin",
        "description": "Danh sách học phần tương đương với Khóa 69 - Khoa CNTT",
        "total_rules": len(equivalents),
        "equivalents": equivalents
    }

    os.makedirs(os.path.dirname(output_yaml_path), exist_ok=True)
    with open(output_yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    print(f"K69 Equivalents: Successfully generated {len(equivalents)} rules at {output_yaml_path}")


if __name__ == "__main__":
    k68_excel = r"C:\Users\HA ANH\Documents\KLTN\v1\documents\information_technology\danh_sach_hoc_phan_tuong_duong_k68_CNTT.xlsx"
    out_k68_yaml = r"c:\Users\HA ANH\Documents\KLTN\KLTN\data\equivalents_k68.yaml"
    build_k68_equivalents(k68_excel, out_k68_yaml)

    k69_md = r"test_parsed\k69_equiv\DS-hoc-phan-tuong-duong-voi-K69.md"
    out_k69_yaml = r"c:\Users\HA ANH\Documents\KLTN\KLTN\data\equivalents_k69.yaml"
    build_k69_equivalents(k69_md, out_k69_yaml)
