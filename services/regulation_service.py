import os
import json
import re
import math
from collections import Counter
from typing import List, Dict, Any

CHUNKS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "quy_che_chunks.json"))

_REGULATIONS: List[dict] = []
_IDF: Dict[str, float] = {}
_LAST_MTIME: float = 0.0

def load_regulations() -> List[dict]:
    global _REGULATIONS, _IDF, _LAST_MTIME
    if not os.path.exists(CHUNKS_PATH):
        return []

    current_mtime = os.path.getmtime(CHUNKS_PATH)
    if _REGULATIONS and current_mtime == _LAST_MTIME:
        return _REGULATIONS

    with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        _REGULATIONS = data.get("articles", [])
    _LAST_MTIME = current_mtime

    # Build IDF dictionary
    doc_count = len(_REGULATIONS)
    df = Counter()
    for art in _REGULATIONS:
        text = (art.get("title", "") + " " + art.get("content", "")).lower()
        words_in_doc = set(re.findall(r"\w+", text))
        for w in words_in_doc:
            df[w] += 1
    _IDF = {w: math.log((doc_count + 1) / (cnt + 1)) + 1.0 for w, cnt in df.items()}

    return _REGULATIONS

def search_regulations(query: str, top_k: int = 4) -> List[dict]:
    """
    Tra cứu các điều khoản trong Quy chế đào tạo và Sổ tay sinh viên phù hợp nhất với câu hỏi.
    Sử dụng TF-IDF scoring kết hợp độ phủ từ khóa (Query Coverage), cụm từ n-gram
    và cơ chế đa dạng hóa kết quả (MMR Diversity) để không bị một Điều chiếm hết top_k.
    """
    articles = load_regulations()
    if not articles:
        return [{"error": "Chưa nạp được dữ liệu quy chế đào tạo."}]

    q_clean = query.strip().lower()
    words = [w for w in re.findall(r"\w+", q_clean) if len(w) >= 2]
    if not words:
        return articles[:top_k]

    unique_q_words = set(words)
    dieu_match = re.search(r"điều\s+(\d+)", q_clean)
    target_article_num = int(dieu_match.group(1)) if dieu_match else None

    scored = []
    for art in articles:
        title_lower = art.get("title", "").lower()
        content_lower = art.get("content", "").lower()
        full_text_lower = title_lower + " \n " + content_lower

        score = 0.0

        # Exact full query match
        if q_clean in title_lower:
            score += 100.0
        if q_clean in content_lower:
            score += 60.0

        # Article number mention e.g. "điều 18" -> art.article_number == 18
        if target_article_num is not None and art.get("article_number") == target_article_num:
            score += 250.0

        # TF-IDF keyword match & Query Coverage (Độ phủ từ khóa của câu hỏi)
        c_words = re.findall(r"\w+", content_lower)
        tf = Counter(c_words)
        matched_unique_words = 0
        matched_idf_sum = 0.0

        for w in unique_q_words:
            w_idf = _IDF.get(w, 1.0)
            in_title = w in title_lower
            in_content = w in tf
            if in_title or in_content:
                matched_unique_words += 1
                matched_idf_sum += w_idf
            if in_title:
                score += w_idf * 3.5
            if in_content:
                score += w_idf * (2.0 + math.log(tf[w]))

        # Thưởng lớn cho Chunk bao phủ được nhiều từ khóa khác nhau của câu hỏi
        # (Ví dụ: vừa có 'khóa luận tốt nghiệp' vừa có 'đăng ký', 'tối đa', 'tín chỉ')
        coverage_ratio = matched_unique_words / len(unique_q_words)
        score += (coverage_ratio ** 2) * matched_idf_sum * 4.0

        # Bigram & Trigram match for multi-word phrases
        matched_bigrams = 0
        for i in range(len(words) - 1):
            bigram = f"{words[i]} {words[i+1]}"
            in_b_title = bigram in title_lower
            in_b_content = bigram in content_lower
            if in_b_title:
                score += 18.0
            if in_b_content:
                score += 22.0
            if in_b_title or in_b_content:
                matched_bigrams += 1

        for i in range(len(words) - 2):
            trigram = f"{words[i]} {words[i+1]} {words[i+2]}"
            if trigram in full_text_lower:
                score += 35.0

        if score > 0:
            scored.append((score, art))

    scored.sort(key=lambda x: x[0], reverse=True)

    # Áp dụng nguyên lý MMR (Đa dạng hóa kết quả):
    # Nếu người dùng không hỏi đích danh 1 Điều cụ thể, giới hạn tối đa 2 phần (sub-chunks)
    # từ cùng một Điều/Mục để tránh trường hợp 1 Điều dài (như Điều 25 có 4 phần) chiếm hết top_k,
    # làm mất cơ hội xuất hiện của Điều liên quan khác (như Điều 13 Khoản 10).
    results = []
    article_counts = Counter()
    max_per_group = top_k if target_article_num is not None else 2

    for score, art in scored:
        group_key = art.get("article_number") or art.get("title", "").split(" (Phần")[0]
        if article_counts[group_key] >= max_per_group:
            continue
        results.append(art)
        article_counts[group_key] += 1
        if len(results) >= top_k:
            break

    if not results:
        return [{"message": "Không tìm thấy điều khoản trực tiếp phù hợp. Vui lòng cung cấp thêm từ khóa cụ thể."}]

    return results



