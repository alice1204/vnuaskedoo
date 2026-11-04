import os
import json
import time
from typing import Dict, Generator, Optional, Any
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ClientError

from services.knowledge_service import (
    get_curriculum_courses,
    lookup_equivalent_courses,
)
from services.regulation_service import search_regulations
from services.academic_rules import get_candidate_courses, get_student
from services.student_service import get_current_student_id
from services.scheduler import create_schedule
from services.data_loader import (
    load_grades,
    get_student_grades_summary,
)
from services.grade_calculator import (
    calculate_required_final_score,
)


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

FALLBACK_MODELS = [
    GEMINI_MODEL,
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-flash-lite-latest",
]
# Remove duplicates while preserving order
FALLBACK_MODELS = list(dict.fromkeys(FALLBACK_MODELS))

client = genai.Client(api_key=GEMINI_API_KEY)

# Tool 1: Tra cứu tiến trình đào tạo K67 - K70
def tool_lookup_curriculum(cohort: str, semester: Optional[int] = None, search_term: Optional[str] = None) -> str:
    """
    Tra cứu tiến trình chương trình đào tạo của Khoa CNTT cho các khóa K67, K68, K69, K70.
    Dùng để kiểm tra thông tin môn học, số tín chỉ, học kỳ, điều kiện tiên quyết, và phân loại đặc thù
    (ví dụ: phân biệt môn tự chọn thường ở kỳ 1-7 với môn tự chọn chỉ dùng để thay thế Khóa luận tốt nghiệp ở kỳ 8).
    Args:
        cohort: Khóa sinh viên cần tra cứu, ví dụ 'K67', 'K68', 'K69', 'K70'.
        semester: Học kỳ dự kiến (từ 1 đến 8), có thể để None nếu muốn xem toàn khóa hoặc tìm theo tên môn.
        search_term: Tên môn học hoặc mã học phần cần tìm kiếm (ví dụ: 'Toán giải tích', 'Truyền thông đa phương tiện', 'TH02046').
    """
    results = get_curriculum_courses(cohort=cohort, semester=semester, search_term=search_term)
    if not results:
        return f"Không tìm thấy học phần nào phù hợp trong CTĐT khóa {cohort}."
    # Giới hạn thông tin gọn nhẹ nhưng giữ đầy đủ quy tắc đặc thù của học phần bằng tiếng Việt
    type_map = {
        "compulsory": "Bắt buộc",
        "elective": "Tự chọn",
        "conditional": "Điều kiện",
    }
    compact_results = []
    for r in results[:10]:
        item = {
            "code": r.get("code"),
            "ma_mon": r.get("code"),
            "name": r.get("name"),
            "ten_mon": r.get("name"),
            "credits": r.get("credits"),
            "so_tin_chi": r.get("credits"),
            "semester": r.get("semester"),
            "hoc_ky": r.get("semester"),
            "type": r.get("type"),
            "phan_loai": r.get("category", type_map.get(r.get("type"), "Tự chọn")),
            "prerequisites": r.get("prerequisites", []),
            "mon_tien_quyet": r.get("prerequisites", []),
        }
        if "specialization_group" in r:
            item["dinh_huong_chuyen_sau"] = r["specialization_group"]
        if "note" in r:
            item["ghi_chu_quy_dinh"] = r["note"]
        compact_results.append(item)
    return json.dumps(compact_results, ensure_ascii=False)

# Tool 2: Tra cứu học phần tương đương và thay thế K68, K69
def tool_lookup_equivalent_course(cohort: str, query: str) -> str:
    """
    Tra cứu học phần tương đương hoặc học phần thay thế cho sinh viên K68 hoặc K69 của Khoa CNTT.
    Dùng khi sinh viên bị nợ môn cũ, muốn biết môn mới thay thế là môn gì hoặc ngược lại.
    Args:
        cohort: Khóa cần tra cứu ('K68' hoặc 'K69').
        query: Tên học phần hoặc mã học phần cần tra cứu (ví dụ: 'Xác suất thống kê', 'TH01007', 'TH02016').
    """
    results = lookup_equivalent_courses(cohort=cohort, query=query)
    if not results:
        return f"Không tìm thấy quy tắc học phần tương đương nào cho '{query}' trong danh mục của {cohort}."
    return json.dumps(results[:8], ensure_ascii=False)

# Tool 3: Tra cứu Quy chế đào tạo và Sổ tay sinh viên
def tool_search_regulations(query: str) -> str:
    """
    Tra cứu các điều khoản trong Quy chế đào tạo đại học và Sổ tay sinh viên của Học viện Nông nghiệp Việt Nam.
    Dùng để trả lời các câu hỏi về: điều kiện cảnh báo học tập, buộc thôi học, thang điểm, điều kiện xét tốt nghiệp,
    rút học phần, học lại, học cải thiện, nghỉ học tạm thời, điểm rèn luyện, học bổng, miễn giảm học phí, quy đổi tiếng Anh.
    Args:
        query: Từ khóa hoặc câu hỏi cần tra cứu quy chế (ví dụ: 'cảnh báo học tập', 'học bổng khuyến khích', 'quy đổi tiếng Anh', 'miễn giảm học phí').
    """
    results = search_regulations(query=query, top_k=4)
    compact_chunks = []
    for art in results:
        if "error" in art or "message" in art:
            compact_chunks.append(art)
            continue
        content = art.get("content", "")
        # Rút gọn nội dung nếu quá dài (tối đa 1400 ký tự - vừa khít với kích thước chunk mới)
        if len(content) > 1400:
            content = content[:1400] + "... [xem tiếp trong quy chế]"
        compact_chunks.append({
            "title": art.get("title"),
            "content": content
        })
    return json.dumps(compact_chunks, ensure_ascii=False)

# Tool 4: Tự động xếp thời khóa biểu dựa trên thuật toán Rule-based Scheduler
def tool_generate_schedule(student_id: str = "671234", target_credits: int = 18, allow_early: bool = True) -> str:
    """
    Tự động xếp lịch học đề xuất cho sinh viên dựa trên tình trạng học tập thực tế, các môn đã học, nợ môn và môn mở.
    Args:
        student_id: Mã sinh viên (mặc định lấy mã sinh viên đang đăng nhập).
        target_credits: Số tín chỉ mong muốn đăng ký (từ 15 đến 25 tín chỉ).
        allow_early: Cho phép đề xuất học vượt môn kỳ tiếp theo nếu thỏa mãn điều kiện tiên quyết.
    """
    try:
        candidates = get_candidate_courses(student_id=student_id, allow_early=allow_early)
        schedule_result = create_schedule(candidates=candidates, target_credits=target_credits)
        return json.dumps(schedule_result, ensure_ascii=False)
    except Exception as e:
        return f"Không thể tạo thời khóa biểu: {str(e)}"

# Tool 5: Tra cứu chi tiết bảng điểm học tập cá nhân
def tool_get_student_grades(student_id: Optional[str] = None) -> str:
    """
    Tra cứu chi tiết bảng điểm học tập của sinh viên: điểm các môn đang học kỳ này (điểm chuyên cần TP1, điểm giữa kỳ TP2),
    danh sách môn đã hoàn thành, môn trượt, GPA tích lũy hệ 4 và hệ 10, tổng tín chỉ tích lũy.
    Dùng khi sinh viên hỏi về điểm số, kết quả học tập, GPA, hoặc tình hình học các môn kỳ này.
    Args:
        student_id: Mã sinh viên cần tra cứu (để trống sẽ tự động lấy mã sinh viên đang đăng nhập).
    """
    try:
        s_id = student_id or get_current_student_id()
        summary = get_student_grades_summary(s_id)
        # Tối ưu dữ liệu gọn gàng cho LLM
        in_prog = []
        for c in summary.get("in_progress_courses", []):
            comps = c.get("components", {})
            in_prog.append({
                "ma_mon": c.get("course_code"),
                "ten_mon": c.get("course_name"),
                "so_tin_chi": c.get("credits"),
                "diem_chuyen_can_tp1": comps.get("tp1", {}).get("score"),
                "diem_giua_ky_tp2": comps.get("tp2", {}).get("score"),
                "trong_so_thi_cuoi_ky_tp3": comps.get("tp3", {}).get("weight", 0.6),
                "trang_thai": "Đang học (Chờ thi cuối kỳ)",
            })

        comp = []
        for c in summary.get("completed_courses", []):
            comp.append({
                "ma_mon": c.get("course_code"),
                "ten_mon": c.get("course_name"),
                "diem_tong_ket_10": c.get("total_score_10"),
                "diem_chu": c.get("letter_grade"),
                "diem_he_4": c.get("gpa_4"),
            })

        fail = []
        for c in summary.get("failed_courses", []):
            fail.append({
                "ma_mon": c.get("course_code"),
                "ten_mon": c.get("course_name"),
                "diem_tong_ket_10": c.get("total_score_10"),
                "diem_chu": "F",
            })

        result = {
            "ma_sinh_vien": s_id,
            "tin_chi_tich_luy": summary.get("passed_credits"),
            "gpa_he_4": summary.get("cumulative_gpa_4"),
            "gpa_he_10": summary.get("cumulative_gpa_10"),
            "mon_dang_hoc_ky_nay": in_prog,
            "mon_da_tich_luy": comp,
            "mon_no_hoc_lai": fail,
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f"Không thể lấy bảng điểm sinh viên: {str(e)}"

# Tool 6: Tính toán điểm thi kết thúc học phần cần đạt (Tư vấn điểm thi)
def tool_calculate_target_exam_score(
    course_name_or_code: str,
    target_letter: Optional[str] = None,
    student_id: Optional[str] = None
) -> str:
    """
    Tính toán điểm thi kết thúc học phần (thi cuối kỳ) tối thiểu cần đạt để đạt các mốc điểm chữ mong muốn (A, B+, B, C+, C, D)
    cho một môn học mà sinh viên đang học.
    Dùng khi sinh viên hỏi 'môn X cần thi mấy điểm để được A / B / qua môn?' hoặc hỏi chiến lược điểm thi.
    Args:
        course_name_or_code: Tên môn học (ví dụ: 'Cơ sở dữ liệu', 'Nguyên lý hệ điều hành') hoặc Mã môn (ví dụ: 'TH02001').
        target_letter: Mức điểm chữ mục tiêu muốn đạt ('A', 'B+', 'B', 'C+', 'C', 'D'). Có thể để None để xem toàn bộ các mốc điểm.
        student_id: Mã sinh viên (để trống sẽ tự động lấy sinh viên đang đăng nhập).
    """
    try:
        s_id = student_id or get_current_student_id()
        grades = load_grades(s_id)
        query_norm = course_name_or_code.strip().lower()

        matched_grade = None
        for g in grades:
            c_code = g.get("course_code", "").lower()
            c_name = g.get("course_name", "").lower()
            if query_norm == c_code or query_norm in c_name or c_name in query_norm:
                matched_grade = g
                break

        if not matched_grade:
            return f"Không tìm thấy học phần '{course_name_or_code}' trong danh sách môn đang học của sinh viên {s_id}."

        components = matched_grade.get("components", {})
        calc = calculate_required_final_score(components, target_letter=target_letter)
        if "error" in calc:
            return calc["error"]

        res = {
            "ma_mon": matched_grade.get("course_code"),
            "ten_mon": matched_grade.get("course_name"),
            "diem_tp1_chuyen_can": components.get("tp1", {}).get("score"),
            "diem_tp2_giua_ky": components.get("tp2", {}).get("score"),
            "trong_so_thi_cuoi_ky": f"{int(calc.get('final_exam_weight', 0.6) * 100)}%",
            "muc_tieu_diem_thi_cuoi_ky": [
                {
                    "diem_chu_mong_muon": t["letter"],
                    "diem_tong_ket_he_10_toi_thieu": t["min_total_10"],
                    "diem_thi_cuoi_ky_can_dat": t["required_final_score"],
                    "tinh_kha_thi": "Khả thi" if t["is_achievable"] else "Không khả thi (vượt quá 10)",
                    "loi_khuyen": t["note"],
                }
                for t in calc["targets"]
            ]
        }
        if calc.get("specific_target"):
            st = calc["specific_target"]
            res["muc_tieu_cu_the"] = {
                "diem_chu": st["letter"],
                "diem_thi_can_dat": st["required_final_score"],
                "loi_khuyen": st["note"],
            }
        return json.dumps(res, ensure_ascii=False)
    except Exception as e:
        return f"Lỗi khi tính toán điểm mục tiêu: {str(e)}"

# Tool 7: Kiểm tra và cảnh báo sớm nguy cơ học vụ
def tool_check_academic_warning(student_id: Optional[str] = None) -> str:
    """
    Kiểm tra và cảnh báo sớm các nguy cơ học vụ của sinh viên: nguy cơ bị cấm thi (nếu điểm chuyên cần < 5.0),
    nguy cơ rớt môn (nếu điểm giữa kỳ < 4.0), hoặc nguy cơ bị cảnh báo học tập theo quy chế Học viện do GPA quá thấp.
    Dùng khi sinh viên hỏi về rủi ro học tập, bị cấm thi, cảnh báo học vụ hoặc tình trạng an toàn học tập.
    Args:
        student_id: Mã sinh viên (để trống sẽ tự động lấy sinh viên đang đăng nhập).
    """
    try:
        s_id = student_id or get_current_student_id()
        summary = get_student_grades_summary(s_id)
        warnings = []
        for c in summary.get("in_progress_courses", []):
            comps = c.get("components", {})
            tp1 = comps.get("tp1", {}).get("score")
            tp2 = comps.get("tp2", {}).get("score")
            name = c.get("course_name")
            code = c.get("course_code")

            if tp1 is not None and tp1 < 5.0:
                warnings.append({
                    "loai_canh_bao": "Nguy cơ cấm thi",
                    "muc_do": "Nguy hiểm",
                    "mon_hoc": f"{name} ({code})",
                    "ly_do": f"Điểm chuyên cần đạt {tp1}/10 (dưới 5.0)",
                    "giai_phap": "Cần liên hệ gấp với giảng viên phụ trách để giải trình điểm danh và làm bổ sung bài tập/nhiệm vụ.",
                })
            elif tp2 is not None and tp2 < 4.0:
                warnings.append({
                    "loai_canh_bao": "Nguy cơ rớt môn",
                    "muc_do": "Cần chú ý",
                    "mon_hoc": f"{name} ({code})",
                    "ly_do": f"Điểm giữa kỳ đạt {tp2}/10",
                    "giai_phap": "Cần tập trung ôn thi cuối kỳ đạt điểm cao để kéo điểm học phần.",
                })

        gpa = summary.get("cumulative_gpa_4", 0.0)
        if gpa > 0 and gpa < 1.5:
            warnings.append({
                "loai_canh_bao": "Cảnh báo học tập tích lũy",
                "muc_do": "Nguy hiểm",
                "mon_hoc": "Toàn khóa",
                "ly_do": f"GPA tích lũy hiện tại là {gpa}/4.0 (gần ngưỡng cảnh báo mức 1)",
                "giai_phap": "Ưu tiên đăng ký học lại môn nợ và học cải thiện các môn điểm D/D+.",
            })

        return json.dumps({
            "ma_sinh_vien": s_id,
            "tong_so_canh_bao": len(warnings),
            "tinh_trang": "An toàn" if len(warnings) == 0 else "Cần chú ý",
            "danh_sach_canh_bao": warnings,
        }, ensure_ascii=False)
    except Exception as e:
        return f"Lỗi khi kiểm tra cảnh báo học vụ: {str(e)}"

SYSTEM_INSTRUCTION = """
Bạn là Cố vấn Học vụ AI của Học viện Nông nghiệp Việt Nam (Khoa Công nghệ thông tin).
Nhiệm vụ của bạn là đồng hành, tư vấn và hỗ trợ cá nhân hóa cho từng sinh viên về:
1. Tiến trình chương trình đào tạo của các khóa K67, K68, K69, K70.
2. Danh mục học phần tương đương và thay thế của K68 và K69.
3. Quy chế đào tạo theo tín chỉ (cảnh báo học tập, buộc thôi học, thang điểm Điều 21, rút môn, xét tốt nghiệp...) và chính sách sinh viên (học bổng, điểm rèn luyện, miễn giảm học phí, quy đổi tiếng Anh).
4. Tự động xếp và gợi ý kế hoạch học tập/thời khóa biểu khi sinh viên yêu cầu.
5. Tư vấn kết quả học tập, phân tích bảng điểm cá nhân, tính toán điểm thi cuối kỳ cần đạt và cảnh báo sớm nguy cơ học vụ.

NGUYÊN TẮC HOẠT ĐỘNG & GIAO TIẾP CÁ NHÂN HÓA:
- PHONG CÁCH GIAO TIẾP: Luôn xưng hô thân mật, lịch sự bằng tên của sinh viên đang đăng nhập (ví dụ: "Chào bạn Văn A", "Theo kết quả học tập của bạn Văn A..."). Giọng văn mang tính đồng cảm, khích lệ và chuyên nghiệp của một Cố vấn học vụ tận tâm.
- SỬ DỤNG DỮ LIỆU NGỮ CẢNH ĐÃ NHÚNG SẴN: Bạn đã được cung cấp sẵn toàn bộ hồ sơ học tập thực tế của sinh viên (Họ tên, khóa, ngành, học kỳ hiện tại, GPA, các môn đang học, điểm chuyên cần TP1, giữa kỳ TP2 và các môn nợ) trong phần [HỒ SƠ HỌC TẬP THỰC TẾ CỦA SINH VIÊN ĐANG ĐĂNG NHẬP] bên dưới.
  + Khi sinh viên hỏi: "Điểm kỳ này của mình thế nào?", "Mình đang học những môn gì?", "GPA của mình ra sao?": Bạn CÓ THỂ sử dụng ngay dữ liệu đã nhúng sẵn hoặc gọi `tool_get_student_grades` để trả lời đầy đủ, chi tiết bằng bảng Markdown đẹp mắt.
  + Khi sinh viên hỏi: "Môn Cơ sở dữ liệu mình cần thi mấy điểm để được A?" (hoặc hỏi về bất kỳ môn nào đang học): Hãy gọi `tool_calculate_target_exam_score` để tính toán chính xác điểm thi cuối kỳ cần đạt, phân tích tính khả thi và đưa ra lời khuyên ôn thi thiết thực.
  + Khi sinh viên hỏi về rủi ro học tập, bị cấm thi hoặc cảnh báo học vụ: Hãy chủ động đối chiếu điểm chuyên cần (TP1 < 5.0) hoặc điểm giữa kỳ (TP2 < 4.0) và gọi `tool_check_academic_warning` để cảnh báo sớm, hướng dẫn giải pháp khắc phục kịp thời.
- TUYỆT ĐỐI KHÔNG BỊA ĐẶT DỮ LIỆU: Chỉ sử dụng thông tin có trong ngữ cảnh hoặc gọi công cụ (tools). Không tự bịa mã môn hay điều khoản quy chế.
- NGÔN TỪ: 100% tiếng Việt tự nhiên. Tuyệt đối KHÔNG viết hoặc để lộ bất kỳ tên biến kỹ thuật tiếng Anh nào (như `tool_get_student_grades`, `calculate_required_final_score`, `in_progress_courses`, `compulsory`...).
- Trình bày câu trả lời bằng Markdown rõ ràng, dễ đọc:
  + Dùng BẢNG (Markdown Table) khi liệt kê môn học, bảng điểm hoặc mục tiêu điểm thi.
  + Trích dẫn nguồn quy chế ngắn gọn ở cuối khi tư vấn (ví dụ: [Nguồn: Điều 21 - Quy chế đào tạo Học viện]).
"""

# In-memory session store (RAM)
_SESSIONS: Dict[str, Any] = {}

def build_student_context_instruction() -> str:
    """
    Lấy thông tin sinh viên đang đăng nhập kèm hồ sơ học tập thực tế
    để nhúng tự động (Personalized Context Injection) vào System Instruction của Gemini.
    """
    try:
        student_id = get_current_student_id()
        student = get_student(student_id)
        if not student:
            return ""

        summary = get_student_grades_summary(student_id)
        gpa_4 = summary.get("cumulative_gpa_4", 0.0)
        gpa_10 = summary.get("cumulative_gpa_10", 0.0)
        passed_credits = summary.get("passed_credits", 0)

        in_progress = summary.get("in_progress_courses", [])
        in_progress_lines = []
        for c in in_progress:
            comps = c.get("components", {})
            tp1 = comps.get("tp1", {}).get("score", "--")
            tp2 = comps.get("tp2", {}).get("score", "--")
            line = f"  * {c.get('course_name')} ({c.get('course_code')}, {c.get('credits')} tín chỉ): Chuyên cần (TP1)={tp1}/10, Giữa kỳ (TP2)={tp2}/10, Thi cuối kỳ (TP3)=Chưa thi (Trọng số 60%)"
            if tp1 != "--" and float(tp1) < 5.0:
                line += " [⚠️ NGUY CƠ CẤM THI DO ĐIỂM CHUYÊN CẦN < 5.0]"
            elif tp2 != "--" and float(tp2) < 4.0:
                line += " [⚠️ NGUY CƠ RỚT MÔN DO ĐIỂM GIỮA KỲ < 4.0]"
            in_progress_lines.append(line)

        failed = summary.get("failed_courses", [])
        failed_lines = [f"{c.get('course_name')} ({c.get('course_code')}, điểm {c.get('total_score_10')})" for c in failed]

        context_text = (
            f"\n[HỒ SƠ HỌC TẬP THỰC TẾ CỦA SINH VIÊN ĐANG ĐĂNG NHẬP]\n"
            f"- Mã sinh viên (student_id): {student_id}\n"
            f"- Họ và tên sinh viên: {student.get('name', 'Không rõ')}\n"
            f"- Khóa (cohort): {student.get('cohort', 'K68')}\n"
            f"- Ngành đào tạo: {student.get('major', 'Khoa học dữ liệu và Trí tuệ nhân tạo')}\n"
            f"- Học kỳ hiện tại: Học kỳ {student.get('current_semester', 1)}\n"
            f"- Tiến độ tích lũy: {passed_credits} tín chỉ\n"
            f"- Điểm trung bình tích lũy: GPA {gpa_4:.2f} / 4.0 (Hệ 10: {gpa_10:.2f} / 10)\n"
            f"- Môn nợ cần học lại: {', '.join(failed_lines) if failed_lines else 'Không có (đã hoàn thành tất cả)'}\n"
            f"- Các môn đang học học kỳ này ({len(in_progress)} môn):\n"
            + ("\n".join(in_progress_lines) if in_progress_lines else "  * Chưa đăng ký môn nào") + "\n"
        )
        return context_text
    except Exception as e:
        return ""

def create_chat_session(model_name: str):
    tools = [
        tool_lookup_curriculum,
        tool_lookup_equivalent_course,
        tool_search_regulations,
        tool_generate_schedule,
        tool_get_student_grades,
        tool_calculate_target_exam_score,
        tool_check_academic_warning,
    ]
    full_system_instruction = SYSTEM_INSTRUCTION + build_student_context_instruction()
    return client.chats.create(
        model=model_name,
        config=types.GenerateContentConfig(
            system_instruction=full_system_instruction,
            temperature=0.2,
            tools=tools,
        ),
    )



def get_or_create_chat(session_id: str, model_name: Optional[str] = None):
    if session_id in _SESSIONS:
        return _SESSIONS[session_id]

    target_model = model_name or FALLBACK_MODELS[0]
    chat = create_chat_session(target_model)
    _SESSIONS[session_id] = chat
    return chat

def chat_agent(message: str, session_id: str = "default_session") -> str:
    for model_name in FALLBACK_MODELS:
        try:
            chat = get_or_create_chat(session_id, model_name=model_name)
            response = chat.send_message(message)
            return response.text
        except Exception as e:
            err_str = str(e)
            if any(k in err_str for k in ["429", "503", "UNAVAILABLE", "RESOURCE_EXHAUSTED"]):
                _SESSIONS.pop(session_id, None)
                continue
            return f"Lỗi xử lý: {err_str}"
    return "Hệ thống đang tiếp nhận nhiều yêu cầu cùng lúc (Rate limit). Bạn vui lòng đợi khoảng 15 giây và thử lại câu hỏi nhé!"

def chat_agent_stream(message: str, session_id: str = "default_session") -> Generator[str, None, None]:
    for model_name in FALLBACK_MODELS:
        try:
            chat = get_or_create_chat(session_id, model_name=model_name)
            response_stream = chat.send_message_stream(message)
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
                _SESSIONS.pop(session_id, None)
                continue
            yield f"Lỗi xử lý: {err_str}"
            return
    yield "Hệ thống đang tiếp nhận nhiều yêu cầu cùng lúc (Rate limit). Bạn vui lòng đợi khoảng 15 giây và thử lại câu hỏi nhé!"

