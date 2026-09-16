import os
import re
import json

def chunk_regulations(md_path: str, output_json_path: str):
    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()

    pattern = r"(?:^|\n)(?:[-#*]+\s*)?(Điều\s+\d+[\.:\s]+[^\n]+)"
    matches = list(re.finditer(pattern, text))

    chunks = []
    for i, match in enumerate(matches):
        raw_title = match.group(1).strip()
        title = re.sub(r"^[#\*\-\s]+", "", raw_title).strip()

        start_idx = match.start()
        end_idx = matches[i + 1].start() if i + 1 < len(matches) else len(text)

        content = text[start_idx:end_idx].strip()

        num_match = re.search(r"Điều\s+(\d+)", title)
        dieu_num = int(num_match.group(1)) if num_match else i + 1

        chunks.append({
            "id": f"dieu_{dieu_num}_{i+1}",
            "article_number": dieu_num,
            "title": title,
            "content": content,
            "char_count": len(content)
        })

    data = {
        "source": "Sổ tay sinh viên & Quy chế đào tạo - Học viện Nông nghiệp Việt Nam",
        "total_articles": len(chunks),
        "articles": chunks
    }

    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Successfully chunked {len(chunks)} articles to {output_json_path}")

if __name__ == "__main__":
    in_md = r"data\quy_che_dao_tao.md"
    out_json = r"data\quy_che_chunks.json"
    chunk_regulations(in_md, out_json)
