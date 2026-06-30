"""
inspect_duplicate.py
---------------------
Pulls full records for a list of chroma_ids and prints all metadata +
caption, so you can compare two (or more) chroma_ids that point at the
same image_path and decide which one is stale/duplicate.

Run from project root:
    $env:PYTHONPATH="."; python scripts/inspect_duplicate.py f5c2d3adf45ff3f1a67e0e93f6a44f72 91a56f1110e1e7bccc0a6320ce31c162
"""

import sys
import chromadb
from config.settings import DB_PATH, IMAGE_COLLECTION


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/inspect_duplicate.py <chroma_id> [<chroma_id> ...]")
        sys.exit(1)

    target_ids = sys.argv[1:]

    db = chromadb.PersistentClient(path=DB_PATH)
    image_col = db.get_collection(IMAGE_COLLECTION)

    results = image_col.get(ids=target_ids, include=["documents", "metadatas"])

    if not results["ids"]:
        print("No matching records found.")
        return

    for chroma_id, doc, meta in zip(results["ids"], results["documents"], results["metadatas"]):
        print("=" * 70)
        print(f"chroma_id: {chroma_id}")
        print("metadata:")
        for k, v in meta.items():
            print(f"  {k}: {v}")
        print("caption:")
        print(doc)
    print("=" * 70)


if __name__ == "__main__":
    main()
