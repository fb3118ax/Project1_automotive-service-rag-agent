"""
recaption_bad_images.py
-----------------------
Finds all ChromaDB image records with numbered callouts (via a GPT-4o
vision classification pass), then re-generates captions via GPT-4o vision
using the callout diagram PLUS rendered images of surrounding manual pages
(not extracted text), so icon-based legends and legends spanning multiple
pages can be read visually instead of relying on pdfplumber text extraction.

Captions are written as natural-language prose (each numbered callout is
described in a full sentence that keeps its item number) so they embed well
against natural-language queries instead of as a bare numbered list.

Requires the original PDF (PDF_PATH) since pages are rasterized on demand.

Run from project root:
    PYTHONPATH="." python scripts/recaption_bad_images.py

Dry run (classification only, no API spend on recaptioning):
    PYTHONPATH="." python scripts/recaption_bad_images.py --dry-run

Safety cap: if more than SAFETY_CAP images are flagged, the script prints
a cost estimate and requires --confirm to proceed.
"""

import argparse
import base64
import os
from io import BytesIO

import chromadb
import pdfplumber

from config.settings import DB_PATH, IMAGE_COLLECTION, LLM_MODEL, client, embedding_model, PDF_PATH

SAFETY_CAP = 50
PAGE_FORWARD = 2  # legends only ever appear on the callout page or after it;
                   # render page_number .. page_number + PAGE_FORWARD


def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    ext = image_path.rsplit(".", 1)[-1].lower()
    mime = "image/png" if ext == "png" else "image/jpeg"
    return f"data:{mime};base64,{b64}"


def is_numbered_callout(image_path: str, client) -> bool:
    """Cheap classification pass: does this image have numbered callouts?"""
    if not os.path.exists(image_path):
        return False
    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            temperature=0,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Does this image contain numbered callouts (circled numbers with leader lines pointing to components)? Answer only 'yes' or 'no'."},
                    {"type": "image_url", "image_url": {"url": encode_image(image_path)}}
                ]
            }],
            max_tokens=5,
        )
        answer = resp.choices[0].message.content.strip().lower()
        return answer.startswith("yes")
    except Exception as e:
        print(f"  [classify error] {image_path}: {e}")
        return False


def find_bad_records(col, client):
    """
    Return list of (chroma_id, image_path, meta) for images with numbered
    callouts. Deduplicates by image_path so the same file isn't classified
    or recaptioned twice if multiple chroma_ids point at it.
    """
    results = col.get(include=["documents", "metadatas"])
    bad = []
    seen_paths = set()
    total = len(results["ids"])
    for i, (chroma_id, doc, meta) in enumerate(
        zip(results["ids"], results["documents"], results["metadatas"])
    ):
        path = meta.get("image_path", "")
        if path in seen_paths:
            print(f"  [{i+1}/{total}] {path} ... duplicate path, skipping reclassification")
            continue
        seen_paths.add(path)
        print(f"  [{i+1}/{total}] classifying {path} ...", end=" ")
        if is_numbered_callout(path, client):
            print("NUMBERED CALLOUT — flagged")
            bad.append((chroma_id, path, meta))
        else:
            print("skip")
    return bad


def render_page_as_data_url(pdf, page_number: int, resolution: int = 150) -> str | None:
    """Render a single 1-indexed PDF page to a base64 PNG data URL."""
    try:
        idx = page_number - 1
        if idx < 0 or idx >= len(pdf.pages):
            return None
        page = pdf.pages[idx]
        img = page.to_image(resolution=resolution)
        buf = BytesIO()
        img.original.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{b64}"
    except Exception as e:
        print(f"  [render error] page {page_number}: {e}")
        return None


def generate_caption(image_path: str, page_number: int, pdf, forward: int = PAGE_FORWARD) -> str | None:
    """
    Generate a caption using the callout diagram + rendered images of
    surrounding manual pages, so GPT-4o can read icon-based or
    multi-page legends visually.

    The caption is returned as natural-language prose: a sentence describing
    the diagram overall followed by one sentence per numbered callout that
    keeps the item number (e.g. "Item 1 is the safety switch ..."), so the
    text embeds well against natural-language queries instead of as a bare
    numbered list.

    Only forward pages are rendered (page_number .. page_number + forward).
    Legends in this manual are confirmed to never appear on a page before
    the callout image, so a backward window is wasted cost.
    """
    if not os.path.exists(image_path):
        print(f"  [SKIP] File not found: {image_path}")
        return None
    try:
        content = [
            {"type": "image_url", "image_url": {"url": encode_image(image_path)}},
        ]

        for p in range(page_number, page_number + forward + 1):
            page_url = render_page_as_data_url(pdf, p)
            if page_url:
                content.append({"type": "image_url", "image_url": {"url": page_url}})

        content.append({
            "type": "text",
            "text": (
                "The first image is a numbered-callout diagram from a vehicle service manual "
                "(components marked with circled numbers and leader lines). "
                "The following image(s) are the surrounding manual pages, which contain the "
                "legend mapping each number to a component name (the legend may use icons "
                "next to text labels, and may span more than one page). "
                "Using the legend pages, write a natural-language description of the diagram "
                "in flowing prose, NOT as a bare numbered list. "
                "Begin with one sentence describing what the diagram shows overall, then "
                "describe each numbered callout in its own sentence that keeps the item "
                "number, for example: 'This diagram shows the vehicle controls layout. "
                "Item 1 is the safety switch for windows and roller sunblinds. Item 2 is "
                "the window lifter controls.' "
                "Be specific and technical so the description is useful for a technician "
                "searching in natural language. "
                "If a number genuinely cannot be matched to a legend entry, write a sentence "
                "for that item only stating exactly: No match in the provided legend."
            ),
        })

        response = client.chat.completions.create(
            model=LLM_MODEL,
            timeout=90,
            messages=[{"role": "user", "content": content}],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"  [ERROR] {image_path}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm", action="store_true", help="Skip the safety cap prompt")
    args = parser.parse_args()

    db = chromadb.PersistentClient(path=DB_PATH)
    image_col = db.get_collection(IMAGE_COLLECTION)

    print(f"Total images in collection: {image_col.count()}")

    bad_records = find_bad_records(image_col, client)
    print(f"Found {len(bad_records)} numbered-callout images.")

    if args.dry_run:
        for chroma_id, path, _ in bad_records:
            print(f"  {path}")
        return

    if len(bad_records) > SAFETY_CAP and not args.confirm:
        images_per_call = 1 + (PAGE_FORWARD + 1)  # callout + context pages
        print(
            f"\n[SAFETY CAP] {len(bad_records)} images flagged, exceeding cap of {SAFETY_CAP}.\n"
            f"Each recaption call sends ~{images_per_call} images "
            f"(callout + {PAGE_FORWARD + 1} forward context pages), so this run will make "
            f"{len(bad_records)} vision calls totalling ~{len(bad_records) * images_per_call} images.\n"
            f"Re-run with --confirm to proceed anyway.\n"
        )
        return

    if not os.path.exists(PDF_PATH):
        print(f"[ERROR] PDF_PATH not found: {PDF_PATH}")
        return

    success = 0
    failed = 0

    with pdfplumber.open(PDF_PATH) as pdf:
        for i, (chroma_id, image_path, meta) in enumerate(bad_records):
            print(f"[{i+1}/{len(bad_records)}] Recaptioning: {image_path}")

            page_number = meta.get("page_number")
            caption = generate_caption(image_path, page_number, pdf)

            if caption:
                emb = embedding_model.embed_query(caption)
                image_col.upsert(
                    ids=[chroma_id],
                    documents=[caption],
                    embeddings=[emb],
                    metadatas=[meta],
                )
                print(f"  [OK] Updated.")
                success += 1
            else:
                failed += 1

    print(f"\nDone. Success: {success}, Failed: {failed}")


if __name__ == "__main__":
    main()
