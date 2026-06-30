"""
recheck_flagged.py
-------------------
Re-runs ONLY the recaption step (not classification) for the 17 pages
already known to have numbered callouts, using the corrected forward-only
PAGE_FORWARD=2 window. Skips the ~368-image classification pass entirely
since we already know which images are flagged.

Prints old caption vs new caption for each, so you can see whether the
window fix actually changed anything for that page (most of the 16 that
already succeeded probably won't change — only ones whose legend extended
to page_number+2 will).

Run from project root:
    $env:PYTHONPATH="."; python scripts/recheck_flagged.py

Add --apply to actually upsert the new captions. Without it, this is a
dry run that only prints the diff.
"""

import argparse
import chromadb

from config.settings import DB_PATH, IMAGE_COLLECTION, embedding_model
from scripts.recaption_bad_images import generate_caption, PAGE_FORWARD, PDF_PATH
import pdfplumber

FLAGGED_PAGES = [36, 38, 50, 130, 135, 164, 168, 187, 209, 271, 310, 315, 350, 404, 406, 407, 428]

# If you already have the exact chroma_ids for the 17 flagged records, paste
# them here instead of relying on FLAGGED_PAGES resolution below — this is
# the authoritative, collision-proof identifier (page_number is not
# guaranteed unique, see dedup logic in recaption_bad_images.py).
KNOWN_CHROMA_IDS: list[str] = [
    # "164de1897a6fa48e7996f7622374528f",  # page 36
]

# Per-record override: some flagged images (e.g. page 404) are self-explanatory
# step-by-step illustrations with arrow labels explained in the page's own
# body text — they don't need a forward legend page, and adding one can
# confuse the model about which image is the actual diagram (seen on
# chroma_id 698fd56d93fe272caa813edd2589c13c). Set forward=0 for those.
FORWARD_OVERRIDES: dict[str, int] = {
    "698fd56d93fe272caa813edd2589c13c": 0,  # page 404, image_1 — self-contained, no legend page needed
    "00e8cd083fc4c07a9c44ebc5e0314d40": 0,  # page 406 — numbered legend (1-7) is on the same page, no forward page needed
    "489dbcf90b9b0bbca0ea0e43dcbf2707": 0,  # page 407 — numbered legend (1-7) is on the same page, no forward page needed
    "859caa2924b1c8000f69db177440f5be": 0,  # page 350, image_0 — arrows reference inline step text, not a legend page
    "7b888d57bbae64e4e0b8481b08eb651a": 0,  # page 350, image_1 — same self-contained pattern
    "50799275ef5e472bc044e111efd37f20": 0,  # page 350, image_2 — same self-contained pattern
    "1185a591432e19541bdccf76f30be106": 0,  # page 350, image_3 — same self-contained pattern
    "5b9b2a18b59e2b5de3864c89b117b8be": 0,  # page 135, image_1 — numbered legend (1-6) is on the same page

    # Page 271 has THREE separate numbered diagrams, each with its own
    # legend listed directly below it, all on page 271 itself (confirmed via
    # screenshot). Page 272's content is a different, unrelated icon-meaning
    # table, not a continuation of these legends — forward=0 is correct.
    "a12eae2c458ecd0ab524594a5c16a280": 0,  # page 271, image_0
    "92e9941712807eace73fe70cbf595229": 0,  # page 271, image_1
    "f5c2d3adf45ff3f1a67e0e93f6a44f72": 0,  # page 271, image_2
}


def resolve_chroma_ids(image_col):
    """
    Build the authoritative list of (chroma_id, doc, meta) to re-recaption.
    Prefers KNOWN_CHROMA_IDS if populated; otherwise falls back to resolving
    chroma_ids from FLAGGED_PAGES via page_number, then locks to chroma_id
    for everything after this point.
    """
    results = image_col.get(include=["documents", "metadatas"])
    by_id = {
        chroma_id: (doc, meta)
        for chroma_id, doc, meta in zip(results["ids"], results["documents"], results["metadatas"])
    }

    if KNOWN_CHROMA_IDS:
        resolved = []
        for chroma_id in KNOWN_CHROMA_IDS:
            if chroma_id not in by_id:
                print(f"[WARN] chroma_id {chroma_id} not found in collection, skipping")
                continue
            doc, meta = by_id[chroma_id]
            resolved.append((chroma_id, doc, meta))
        return resolved

    # Fallback: resolve by page_number once, then key everything by chroma_id
    resolved = []
    seen_ids = set()
    for chroma_id, (doc, meta) in by_id.items():
        if meta.get("page_number") in FLAGGED_PAGES and chroma_id not in seen_ids:
            seen_ids.add(chroma_id)
            resolved.append((chroma_id, doc, meta))

    pages_found = {meta.get("page_number") for _, _, meta in resolved}
    missing = [p for p in FLAGGED_PAGES if p not in pages_found]
    if missing:
        print(f"[WARN] No record found for pages: {missing}")
    dupes = [p for p in pages_found if sum(1 for _, _, m in resolved if m.get("page_number") == p) > 1]
    if dupes:
        print(f"[WARN] Multiple chroma_ids share page_number for pages: {dupes} — "
              f"both will be re-recaptioned since chroma_id is now the key.")
    return resolved


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Actually upsert new captions (default is dry-run/diff-only)")
    parser.add_argument("--chroma-id", type=str, default=None, help="Only process this single chroma_id (for testing one record at a time)")
    args = parser.parse_args()

    db = chromadb.PersistentClient(path=DB_PATH)
    image_col = db.get_collection(IMAGE_COLLECTION)

    records = resolve_chroma_ids(image_col)

    if args.chroma_id:
        records = [r for r in records if r[0] == args.chroma_id]
        if not records:
            print(f"[ERROR] chroma_id {args.chroma_id} not found among resolved records.")
            return

    print(f"Resolved {len(records)} chroma_id-keyed records to re-recaption.")
    print("Resolved chroma_ids (save these into KNOWN_CHROMA_IDS for future runs):")
    for chroma_id, _, meta in records:
        print(f"  \"{chroma_id}\",  # page {meta.get('page_number')}")

    changed = 0
    unchanged = 0
    failed = 0

    with pdfplumber.open(PDF_PATH) as pdf:
        for chroma_id, old_caption, meta in records:
            image_path = meta.get("image_path", "")
            page_number = meta.get("page_number")
            print(f"\n=== chroma_id {chroma_id} | page {page_number} ({image_path}) ===")

            forward = FORWARD_OVERRIDES.get(chroma_id, PAGE_FORWARD)
            new_caption = generate_caption(image_path, page_number, pdf, forward=forward)
            if not new_caption:
                print("  [FAILED to regenerate]")
                failed += 1
                continue

            if new_caption.strip() == old_caption.strip():
                print("  [UNCHANGED]")
                unchanged += 1
                continue

            changed += 1
            print("  [CHANGED]")
            print(f"  OLD: {old_caption[:300]}{'...' if len(old_caption) > 300 else ''}")
            print(f"  NEW: {new_caption[:300]}{'...' if len(new_caption) > 300 else ''}")

            if args.apply:
                emb = embedding_model.embed_query(new_caption)
                image_col.upsert(
                    ids=[chroma_id],
                    documents=[new_caption],
                    embeddings=[emb],
                    metadatas=[meta],
                )
                print("  [UPSERTED]")

    print(f"\nDone. Changed: {changed}, Unchanged: {unchanged}, Failed: {failed}")
    if changed and not args.apply:
        print("This was a dry run — re-run with --apply to save the changed captions.")


if __name__ == "__main__":
    main()