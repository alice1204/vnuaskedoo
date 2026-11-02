import os
import re
import sys
import json
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MD_PATH = os.path.join(BASE_DIR, "data", "quy_che_dao_tao.md")
OUT_JSON_PATH = os.path.join(BASE_DIR, "data", "quy_che_chunks.json")


def preprocess_markdown_for_splitting(raw_md: str) -> str:
    """
    Chuẩn hóa phân cấp tiêu đề Markdown theo đúng thứ tự từ lớn đến nhỏ (# -> ## -> ### -> ####)
    để MarkdownHeaderTextSplitter tự động reset ngữ cảnh khi sang Chương/Phụ lục mới:
      - # (Level 1)   : Văn bản lớn (từ '## ' gốc)
      - ## (Level 2)  : Chương / Phụ lục / Hướng dẫn lớn (từ '##### ' hoặc '#### ' gốc)
      - ### (Level 3) : Điều khoản ('Điều X.') hoặc Mục lớn ('- A. MIỄN, GIẢM HỌC PHÍ'...)
      - #### (Level 4): Tiểu mục ('###### ' gốc)
    """
    lines = raw_md.splitlines()
    processed_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            processed_lines.append("# " + stripped[3:].strip())
        elif stripped.startswith("##### ") or stripped.startswith("#### "):
            clean = re.sub(r"^#+\s*", "", stripped)
            processed_lines.append("## " + clean)
        elif stripped.startswith("###### "):
            clean = re.sub(r"^#+\s*", "", stripped)
            processed_lines.append("#### " + clean)
        # Chuyển "- Điều 15. Đăng ký học lại" hoặc "Điều 15. ..." thành "### Điều 15. ..."
        elif re.match(r"^(?:-\s*)?Điều\s+\d+[\.\:]\s+.+", stripped):
            clean_title = re.sub(r"^-\s*", "", stripped)
            processed_lines.append(f"### {clean_title}")
        # Chuyển "- A. MIỄN, GIẢM HỌC PHÍ", "- E. HỌC BỔNG KHUYẾN KHÍCH HỌC TẬP" thành "### A. ..."
        elif re.match(r"^-\s+[A-H]\.\s+[A-ZÀ-Ỹ0-9\s,\-]+$", stripped):
            clean_title = re.sub(r"^-\s*", "", stripped)
            processed_lines.append(f"### {clean_title}")
        else:
            processed_lines.append(line)

    return "\n".join(processed_lines)


def build_chunks():
    with open(MD_PATH, "r", encoding="utf-8") as f:
        raw_md = f.read()

    normalized_md = preprocess_markdown_for_splitting(raw_md)

    # BƯỚC 1: Dùng MarkdownHeaderTextSplitter (Bài 2 khóa học LangChain)
    headers_to_split_on = [
        ("#", "doc_section"),
        ("##", "chapter"),
        ("###", "article_or_topic"),
        ("####", "sub_topic"),
    ]
    md_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False,
    )
    md_docs = md_splitter.split_text(normalized_md)

    # BƯỚC 2: Dùng RecursiveCharacterTextSplitter để chia nhỏ các Điều/Phụ lục dài > 1150 ký tự
    recursive_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1100,
        chunk_overlap=150,
        separators=["\n\n", "\n- ", "\n|", "\n", " "],
    )

    final_articles = []
    chunk_counter = 1

    for doc in md_docs:
        meta = doc.metadata
        chapter = meta.get("chapter", "").strip()
        article_or_topic = meta.get("article_or_topic", "").strip()
        sub_topic = meta.get("sub_topic", "").strip()

        # Bỏ qua phần MỤC LỤC ở đầu file
        if chapter == "MỤC LỤC":
            continue

        # Xác định tiêu đề rõ ràng nhất cho chunk
        title_parts = []
        if article_or_topic:
            title_parts.append(article_or_topic)
        elif chapter:
            title_parts.append(chapter)

        if sub_topic and sub_topic not in title_parts:
            # Bỏ qua các sub_topic chỉ là số trang như "2"
            if not sub_topic.isdigit() and len(sub_topic) < 120:
                title_parts.append(sub_topic)

        base_title = " - ".join(title_parts) if title_parts else meta.get("doc_section", "Quy chế đào tạo")

        # Trích xuất số Điều (nếu có)
        article_number = 0
        m_art = re.search(r"Điều\s+(\d+)", base_title)
        if m_art:
            article_number = int(m_art.group(1))

        content = doc.page_content.strip()
        if len(content) < 40:
            continue

        # Nếu đoạn văn dài hơn 1150 ký tự, chia nhỏ bằng RecursiveCharacterTextSplitter
        if len(content) > 1150:
            sub_texts = recursive_splitter.split_text(content)
            for idx, sub_text in enumerate(sub_texts, start=1):
                part_title = f"{base_title} (Phần {idx}/{len(sub_texts)})" if len(sub_texts) > 1 else base_title
                # Đảm bảo mỗi sub-chunk đều có tiêu đề ở dòng đầu để không mất ngữ cảnh
                if base_title not in sub_text[:150]:
                    full_content = f"{part_title}\n\n{sub_text}"
                else:
                    full_content = sub_text

                chunk_id = f"dieu_{article_number}_{chunk_counter}" if article_number else f"muc_{chunk_counter}"
                final_articles.append({
                    "id": chunk_id,
                    "article_number": article_number,
                    "section": chapter or meta.get("doc_section", ""),
                    "title": part_title,
                    "content": full_content,
                    "char_count": len(full_content),
                })
                chunk_counter += 1
        else:
            chunk_id = f"dieu_{article_number}_{chunk_counter}" if article_number else f"muc_{chunk_counter}"
            final_articles.append({
                "id": chunk_id,
                "article_number": article_number,
                "section": chapter or meta.get("doc_section", ""),
                "title": base_title,
                "content": content,
                "char_count": len(content),
            })
            chunk_counter += 1

    output_data = {
        "source": "Sổ tay sinh viên & Quy chế đào tạo - Học viện Nông nghiệp Việt Nam",
        "total_articles": len(final_articles),
        "articles": final_articles,
    }

    with open(OUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    max_len = max(a["char_count"] for a in final_articles)
    avg_len = sum(a["char_count"] for a in final_articles) // len(final_articles)
    print(f"Đã chia lại thành công file quy_che_chunks.json!")
    print(f"- Tổng số chunks mới: {len(final_articles)} (trước đây: 69)")
    print(f"- Độ dài trung bình: {avg_len} ký tự/chunk")
    print(f"- Độ dài lớn nhất: {max_len} ký tự/chunk (trước đây: 64.019 ký tự)")


if __name__ == "__main__":
    build_chunks()
