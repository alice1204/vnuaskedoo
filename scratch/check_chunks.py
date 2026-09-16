import json
import re
import math
from collections import Counter

with open('data/quy_che_chunks.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

articles = data.get('articles', [])

# Calculate IDF for all words across all articles
doc_count = len(articles)
df = Counter()
for art in articles:
    text = (art.get("title", "") + " " + art.get("content", "")).lower()
    words_in_doc = set(re.findall(r"\w+", text))
    for w in words_in_doc:
        df[w] += 1

idf = {}
for w, count in df.items():
    idf[w] = math.log((doc_count + 1) / (count + 1)) + 1.0

def search_test(query: str, top_k: int = 3):
    q_clean = query.strip().lower()
    words = [w for w in re.findall(r"\w+", q_clean) if len(w) >= 2]
    
    scored = []
    for art in articles:
        title_lower = art.get("title", "").lower()
        content_lower = art.get("content", "").lower()
        
        score = 0
        # Exact full query match
        if q_clean in title_lower:
            score += 100
        if q_clean in content_lower:
            score += 40
            
        # Article number exact match
        dieu_match = re.search(r"điều\s+(\d+)", q_clean)
        if dieu_match and art.get("article_number") == int(dieu_match.group(1)):
            score += 200
            
        # TF-IDF keyword match
        c_words = re.findall(r"\w+", content_lower)
        tf = Counter(c_words)
        for w in words:
            if w in title_lower:
                score += idf.get(w, 1.0) * 10
            if w in tf:
                score += idf.get(w, 1.0) * (1 + math.log(tf[w]))
                
        # Bigram match for phrase queries
        for i in range(len(words) - 1):
            bigram = f"{words[i]} {words[i+1]}"
            if bigram in title_lower:
                score += 30
            if bigram in content_lower:
                score += 15
                
        if score > 0:
            scored.append((score, art))
            
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]

results = search_test("cảnh báo học tập", top_k=3)
print("Query: 'cảnh báo học tập'")
for s, a in results:
    print(f"  Score {s:.2f}: Art {a.get('article_number')} - {a.get('title')}")

results2 = search_test("buộc thôi học", top_k=3)
print("\nQuery: 'buộc thôi học'")
for s, a in results2:
    print(f"  Score {s:.2f}: Art {a.get('article_number')} - {a.get('title')}")

results3 = search_test("Điều 18", top_k=3)
print("\nQuery: 'Điều 18'")
for s, a in results3:
    print(f"  Score {s:.2f}: Art {a.get('article_number')} - {a.get('title')}")
