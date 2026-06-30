"""
check_page_text.py
-------------------
Dump the raw page text pulled from TEXT_COLLECTION for a given page number,
to debug whether numbered-callout legends are getting truncated at 2000 chars
or are simply not present as extractable text.

Run from project root:
    $env:PYTHONPATH="."; python scripts/check_page_text.py 36
"""

import sys
import chromadb
from config.settings import DB_PATH, TEXT_COLLECTION


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_page_text.py <page_number>")
        sys.exit(1)

    page_number = int(sys.argv[1])

    db = chromadb.PersistentClient(path=DB_PATH)
    text_col = db.get_collection(TEXT_COLLECTION)

    results = text_col.get(include=["documents", "metadatas"])

    chunks = [
        doc for doc, meta in zip(results["documents"], results["metadatas"])
        if meta.get("page_number") == page_number
    ]

    full_text = "\n".join(chunks)
    print(f"Number of chunks for page {page_number}: {len(chunks)}")
    print(f"Total combined length: {len(full_text)} chars")
    print(f"Length actually sent to GPT-4o (first 2000 chars): {min(len(full_text), 2000)}")
    print("-" * 60)
    print("FULL TEXT:")
    print(full_text)


if __name__ == "__main__":
    main()
