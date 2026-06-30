"""
get_chroma_ids.py
------------------
Prints chroma_id, page_number, and image_path for every record in
IMAGE_COLLECTION whose page_number is in FLAGGED_PAGES. Use this output
to fill in KNOWN_CHROMA_IDS at the top of scripts/recheck_flagged.py.

Run from project root:
    $env:PYTHONPATH="."; python scripts/get_chroma_ids.py
"""

import chromadb
from config.settings import DB_PATH, IMAGE_COLLECTION

FLAGGED_PAGES = [36, 38, 50, 130, 135, 164, 168, 187, 209, 271, 310, 315, 350, 404, 406, 407, 428]


def main():
    db = chromadb.PersistentClient(path=DB_PATH)
    image_col = db.get_collection(IMAGE_COLLECTION)

    results = image_col.get(include=["metadatas"])

    matches = [
        (chroma_id, meta.get("page_number"), meta.get("image_path"))
        for chroma_id, meta in zip(results["ids"], results["metadatas"])
        if meta.get("page_number") in FLAGGED_PAGES
    ]
    matches.sort(key=lambda x: x[1])

    found_pages = {pn for _, pn, _ in matches}
    missing = [p for p in FLAGGED_PAGES if p not in found_pages]
    dupes = [p for p in found_pages if sum(1 for _, pn, _ in matches if pn == p) > 1]

    print(f"Found {len(matches)} records for {len(FLAGGED_PAGES)} flagged pages.\n")

    print("KNOWN_CHROMA_IDS = [")
    for chroma_id, page_number, image_path in matches:
        print(f'    "{chroma_id}",  # page {page_number} ({image_path})')
    print("]")

    if missing:
        print(f"\n[WARN] No record found for pages: {missing}")
    if dupes:
        print(f"[WARN] Multiple chroma_ids share page_number for pages: {dupes}")


if __name__ == "__main__":
    main()
