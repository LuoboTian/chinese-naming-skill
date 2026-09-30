#!/usr/bin/env python3
"""在用户提供的本地经典原文目录中检索文本。"""

import argparse
from pathlib import Path

SEARCH_TRANSLATION = str.maketrans(
    "诗经辞风雅颂扬关关雎鸠洲窈窕淑女琴瑟钟鼓乐君子",
    "詩經辭風雅頌揚關關雎鳩洲窈窕淑女琴瑟鐘鼓樂君子",
)


def variants(text):
    traditional = text.translate(SEARCH_TRANSLATION)
    return {text, traditional}


def search(root, query, book=None, limit=20):
    root = Path(root).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"原文目录不存在：{root}")
    matches = []
    book_terms = variants(book) if book else set()
    query_terms = variants(query)
    for path in sorted(root.rglob("*.txt")):
        path_text = str(path)
        if book and not any(term in path_text for term in book_terms):
            continue
        try:
            lines = path.read_text(encoding="utf-8-sig").splitlines()
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(lines, 1):
            if any(term in line for term in query_terms):
                matches.append({
                    "file": str(path.relative_to(root)),
                    "line": number,
                    "text": line.strip(),
                })
                if len(matches) >= limit:
                    return matches
    return matches


def main():
    parser = argparse.ArgumentParser(description="检索本地经典原文")
    parser.add_argument("--root", required=True, help="本地经典原文目录")
    parser.add_argument("--query", required=True, help="要检索的原文或关键词")
    parser.add_argument("--book", help="按文件名或目录筛选，例如：诗经、楚辞、道德经")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    for item in search(args.root, args.query, args.book, args.limit):
        print(f"{item['file']}:{item['line']}: {item['text']}")


if __name__ == "__main__":
    main()
