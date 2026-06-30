"""
find_unresolved_captions.py
---------------------------
Scans the ENTIRE IMAGE_COLLECTION and reports every record whose caption
(`document`) still contains the unresolved-legend marker — i.e. a numbered
callout item the recaption pass could not match to a legend entry.

Use the printed chroma_id list to feed scripts/batch_recheck_flagged.py
(paste it inline or save it to a file passed via --input-file there).

Run from project root:
    PYTHONPATH="." python scripts/find_unresolved_captions.py
"""

import chromadb

from config.settings import DB_PATH, IMAGE_COLLECTION

# Literal marker emitted by the recaption prompt for callout numbers it could
# not match to a legend entry. Kept here as the single source of truth.
UNRESOLVED_MARKER = "No match in the provided legend"


def count_unresolved_lines(document: str) -> int:
    """Number of lines in a caption that contain the unresolved marker."""
    return sum(1 for line in document.splitlines() if UNRESOLVED_MARKER in line)


def main():
    db = chromadb.PersistentClient(path=DB_PATH)
    image_col = db.get_collection(IMAGE_COLLECTION)

    results = image_col.get(include=["documents", "metadatas"])

    total_scanned = len(results["ids"])
    matches = []
    for chroma_id, doc, meta in zip(
        results["ids"], results["documents"], results["metadatas"]
    ):
        document = doc or ""
        if UNRESOLVED_MARKER in document:
            matches.append((
                chroma_id,
                meta.get("page_number"),
                meta.get("image_path"),
                count_unresolved_lines(document),
            ))

    # Sort by page_number; records missing a page_number sort to the end.
    matches.sort(key=lambda m: (m[1] is None, m[1]))

    for chroma_id, page_number, image_path, unresolved_count in matches:
        print(
            f"page {page_number} | {chroma_id} | {image_path} | "
            f"{unresolved_count} unresolved item(s)"
        )

    print("\nchroma_ids = [")
    for chroma_id, page_number, image_path, _ in matches:
        print(f'    "{chroma_id}",  # page {page_number} ({image_path})')
    print("]")

    print(
        f"\nSummary: scanned {total_scanned} records, "
        f"{len(matches)} with at least one unresolved item."
    )


if __name__ == "__main__":
    main()
