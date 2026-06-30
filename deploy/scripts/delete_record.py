"""
delete_record.py
-----------------
Deletes one or more chroma_ids from IMAGE_COLLECTION after manual
confirmation via inspect_duplicate.py. Use only after you've verified
the record is a true orphan/duplicate, not a legitimate entry.

Run from project root:
    $env:PYTHONPATH="."; python scripts/delete_record.py 91a56f1110e1e7bccc0a6320ce31c162
"""

import sys
import chromadb
from config.settings import DB_PATH, IMAGE_COLLECTION


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/delete_record.py <chroma_id> [<chroma_id> ...]")
        sys.exit(1)

    target_ids = sys.argv[1:]

    db = chromadb.PersistentClient(path=DB_PATH)
    image_col = db.get_collection(IMAGE_COLLECTION)

    existing = image_col.get(ids=target_ids, include=["metadatas"])
    if not existing["ids"]:
        print("No matching records found — nothing to delete.")
        return

    print("About to delete:")
    for chroma_id, meta in zip(existing["ids"], existing["metadatas"]):
        print(f"  {chroma_id}  (image_path: {meta.get('image_path')}, page: {meta.get('page_number')})")

    confirm = input("Type 'yes' to confirm deletion: ").strip().lower()
    if confirm != "yes":
        print("Aborted.")
        return

    image_col.delete(ids=existing["ids"])
    print(f"Deleted {len(existing['ids'])} record(s).")


if __name__ == "__main__":
    main()
