"""
spot_check_caption.py
----------------------
Pull a single image record back out of IMAGE_COLLECTION and print its
current caption, so you can eyeball whether the numbered-callout recaption
actually resolved component names correctly.

Run from project root:
    $env:PYTHONPATH="."; python scripts/spot_check_caption.py images/page_36_image_0.png
"""

import sys
import chromadb
from config.settings import DB_PATH, IMAGE_COLLECTION


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/spot_check_caption.py <image_path>")
        sys.exit(1)

    target_path = sys.argv[1]

    db = chromadb.PersistentClient(path=DB_PATH)
    image_col = db.get_collection(IMAGE_COLLECTION)

    results = image_col.get(include=["documents", "metadatas"])

    matches = [
        (chroma_id, doc, meta)
        for chroma_id, doc, meta in zip(
            results["ids"], results["documents"], results["metadatas"]
        )
        if meta.get("image_path", "") == target_path
    ]

    if not matches:
        print(f"No record found with image_path == {target_path}")
        return

    for chroma_id, doc, meta in matches:
        print(f"chroma_id: {chroma_id}")
        print(f"page_number: {meta.get('page_number')}")
        print(f"image_path: {meta.get('image_path')}")
        print("caption:")
        print(doc)
        print("-" * 60)


if __name__ == "__main__":
    main()
