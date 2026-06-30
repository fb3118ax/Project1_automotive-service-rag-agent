"""
batch_recheck_flagged.py
------------------------
Re-runs ONLY the recaption step for an arbitrary batch of chroma_ids
(typically the ones reported by scripts/find_unresolved_captions.py), using
the same forward-window legend logic as scripts/recaption_bad_images.py.

Reuses generate_caption / PAGE_FORWARD / PDF_PATH from recaption_bad_images
so there is a single implementation of the recaption logic.

The batch of chroma_ids comes from either:
  * the inline CHROMA_IDS constant below, or
  * a file passed via --input-file (one chroma_id per line; blank lines and
    lines starting with '#' are ignored). --input-file takes precedence.

Run from project root (dry-run, prints OLD vs NEW only):
    PYTHONPATH="." python scripts/batch_recheck_flagged.py --input-file ids.txt

Apply (actually upsert the regenerated captions):
    PYTHONPATH="." python scripts/batch_recheck_flagged.py --input-file ids.txt --apply

Override the forward window for the whole batch:
    PYTHONPATH="." python scripts/batch_recheck_flagged.py --input-file ids.txt --forward 3
"""

import argparse

import chromadb
import pdfplumber

from config.settings import DB_PATH, IMAGE_COLLECTION, embedding_model
from scripts.recaption_bad_images import generate_caption, PAGE_FORWARD, PDF_PATH

# Same marker as find_unresolved_captions.py — counted after an --apply run as
# a sanity check that recaptioning actually reduced unresolved items.
UNRESOLVED_MARKER = "No match in the provided legend"

# Paste chroma_ids here for a quick run, or pass --input-file (which wins).
CHROMA_IDS: list[str] = [
    # "164de1897a6fa48e7996f7622374528f",
]


def load_chroma_ids(input_file: str | None) -> list[str]:
    """chroma_ids from --input-file if given, else the inline constant."""
    if input_file:
        ids = []
        with open(input_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    ids.append(line)
        return ids
    return list(CHROMA_IDS)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-file",
        type=str,
        default=None,
        help="File with one chroma_id per line (overrides inline CHROMA_IDS)",
    )
    parser.add_argument(
        "--forward",
        type=int,
        default=PAGE_FORWARD,
        help=f"Page-forward window for the whole batch (default {PAGE_FORWARD})",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually upsert regenerated captions (default is dry-run/diff-only)",
    )
    args = parser.parse_args()

    chroma_ids = load_chroma_ids(args.input_file)
    if not chroma_ids:
        print(
            "[ERROR] No chroma_ids provided. Pass --input-file or fill in the "
            "CHROMA_IDS constant."
        )
        return

    db = chromadb.PersistentClient(path=DB_PATH)
    image_col = db.get_collection(IMAGE_COLLECTION)

    results = image_col.get(include=["documents", "metadatas"])
    by_id = {
        chroma_id: (doc, meta)
        for chroma_id, doc, meta in zip(
            results["ids"], results["documents"], results["metadatas"]
        )
    }

    total = len(chroma_ids)
    print(f"Batch of {total} chroma_id(s) | forward={args.forward} | "
          f"{'APPLY' if args.apply else 'DRY-RUN'}")

    changed = 0
    unchanged = 0
    failed = 0
    upserted_ids = []

    with pdfplumber.open(PDF_PATH) as pdf:
        for i, chroma_id in enumerate(chroma_ids):
            print(f"\n[{i+1}/{total}] processing {chroma_id} ...")

            if chroma_id not in by_id:
                print("  [WARN] not found in collection, skipping")
                failed += 1
                continue

            old_caption, meta = by_id[chroma_id]
            old_caption = old_caption or ""
            image_path = meta.get("image_path", "")
            page_number = meta.get("page_number")
            print(f"  page {page_number} | {image_path}")

            new_caption = generate_caption(
                image_path, page_number, pdf, forward=args.forward
            )
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
            print(f"  --- OLD ---\n{old_caption}")
            print(f"  --- NEW ---\n{new_caption}")

            if args.apply:
                emb = embedding_model.embed_query(new_caption)
                image_col.upsert(
                    ids=[chroma_id],
                    documents=[new_caption],
                    embeddings=[emb],
                    metadatas=[meta],
                )
                upserted_ids.append(chroma_id)
                print("  [UPSERTED]")

    print(f"\nDone. Changed: {changed}, Unchanged: {unchanged}, Failed: {failed}")

    if not args.apply:
        if changed:
            print("This was a dry run — re-run with --apply to save the changed captions.")
        return

    # Sanity check: how many unresolved markers remain in what we just wrote.
    if upserted_ids:
        refreshed = image_col.get(ids=upserted_ids, include=["documents"])
        remaining = sum(
            (doc or "").count(UNRESOLVED_MARKER) for doc in refreshed["documents"]
        )
        records_remaining = sum(
            1 for doc in refreshed["documents"] if UNRESOLVED_MARKER in (doc or "")
        )
        print(
            f"Post-apply sanity check: \"{UNRESOLVED_MARKER}\" appears "
            f"{remaining} time(s) across {records_remaining}/{len(upserted_ids)} "
            f"upserted record(s)."
        )


if __name__ == "__main__":
    main()
