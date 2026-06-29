"""
recaption_bad_images.py
-----------------------
Finds all ChromaDB image records where caption == image_path (bad captions),
re-generates captions via GPT-4o vision, and updates ChromaDB in place.

Run from project root:
    $env:PYTHONPATH="."; python scripts/recaption_bad_images.py

Dry run:
    $env:PYTHONPATH="."; python scripts/recaption_bad_images.py --dry-run
"""

import argparse
import base64
import os
import chromadb
from config.settings import DB_PATH, IMAGE_COLLECTION, LLM_MODEL, client, embedding_model


def find_bad_records(col):
    results = col.get(include=["documents", "metadatas"])
    bad = []
    for chroma_id, doc, meta in zip(
        results["ids"], results["documents"], results["metadatas"]
    ):
        path = meta.get("image_path", "")
        if doc.strip() == path.strip():
            bad.append((chroma_id, path, meta))
    return bad


def generate_caption(image_path: str):
    if not os.path.exists(image_path):
        print(f"  [SKIP] File not found: {image_path}")
        return None
    try:
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        response = client.chat.completions.create(
            model=LLM_MODEL,
            timeout=60,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_data}"
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "You are analyzing a BMW service manual image. "
                                "Be specific and technical so the description is useful for a technician "
                                "searching for information. Look for any numbers, labels and text, "
                                "what the image shows, check for symbols and indicators."
                            ),
                        },
                    ],
                }
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"  [ERROR] {image_path}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db = chromadb.PersistentClient(path=DB_PATH)
    col = db.get_collection(IMAGE_COLLECTION)

    bad_records = find_bad_records(col)
    print(f"Found {len(bad_records)} bad captions.")

    if args.dry_run:
        for chroma_id, path, _ in bad_records:
            print(f"  {path}")
        return

    success = 0
    failed = 0

    for i, (chroma_id, image_path, meta) in enumerate(bad_records):
        print(f"[{i+1}/{len(bad_records)}] Recaptioning: {image_path}")
        caption = generate_caption(image_path)

        if caption:
            emb = embedding_model.embed_query(caption)
            col.upsert(
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