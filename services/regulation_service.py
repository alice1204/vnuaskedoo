import os
import json
import re
import math
from collections import Counter
from typing import List, Dict, Any

CHUNKS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "quy_che_chunks.json"))

_REGULATIONS: List[dict] = []
_IDF: Dict[str, float] = {}

def load_regulations() -> List[dict]:
    global _REGULATIONS, _IDF
    if _REGULATIONS:
        return _REGULATIONS
    if os.path.exists(CHUNKS_PATH):
        with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            _REGULATIONS = data.get("articles", [])
        
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

def search_regulations(query: str, top_k: int = 3) -> List[dict]:
    """
    Tra cứu các điều khoản trong Quy chế đào tạo và Sổ tay sinh viên phù hợp nhất với câu hỏi.
    Sử dụng TF-IDF scoring kết hợp cụm từ n-gram và số điều khoản.
    """
    articles = load_regulations()
    if not articles:
        return [{"error": "Chưa nạp được dữ liệu quy chế đào tạo."}]

    q_clean = query.strip().lower()
    words = [w for w in re.findall(r"\w+", q_clean) if len(w) >= 2]
    if not words:
        return articles[:top_k]

    scored = []
    for art in articles:
        title_lower = art.get("title", "").lower()
        content_lower = art.get("content", "").lower()

        score = 0.0

        # Exact full query match
        if q_clean in title_lower:
            score += 100.0
        if q_clean in content_lower:
            score += 40.0

        # Article number mention e.g. "điều 18" -> art.article_number == 18
        dieu_match = re.search(r"điều\s+(\d+)", q_clean)
        if dieu_match and art.get("article_number") == int(dieu_match.group(1)):
            score += 200.0

        # TF-IDF keyword match
        c_words = re.findall(r"\w+", content_lower)
        tf = Counter(c_words)
        for w in words:
            w_idf = _IDF.get(w, 1.0)
            if w in title_lower:
                score += w_idf * 10.0
            if w in tf:
                score += w_idf * (1.0 + math.log(tf[w]))

        # Bigram match for multi-word queries
        for i in range(len(words) - 1):
            bigram = f"{words[i]} {words[i+1]}"
            if bigram in title_lower:
                score += 30.0
            if bigram in content_lower:
                score += 15.0

        if score > 0:
            scored.append((score, art))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = [item[1] for item in scored[:top_k]]

    if not results:
        return [{"message": "Không tìm thấy điều khoản trực tiếp phù hợp. Vui lòng cung cấp thêm từ khóa cụ thể."}]

    return results


