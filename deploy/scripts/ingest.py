import os
import pickle
import argparse
from scripts.loader import loader_doc
from scripts.chunker import chunker
from scripts.image_processor import image_processor
from scripts.vector_store import vector_store
from config.settings import EXTRACTED_IMAGES, TEXT_COLLECTION, TABLE_COLLECTION, IMAGE_COLLECTION

def main():
    # parse --rebuild flag
    parser = argparse.ArgumentParser() # argparse is Python's built-in library for handling command line arguments.argparse reads --rebuild and sets args.rebuild = True.args.rebuild = False by default.
    parser.add_argument("--rebuild", action="store_true", help="Wipe and rebuild the vector DB")
    args = parser.parse_args()

    # step 1 — load and clean PDF
    print("Loading PDF...")
    text_doc, table_doc, image_doc = loader_doc()
    print(f"Loaded: {len(text_doc)} text pages, {len(table_doc)} table pages, {len(image_doc)} image pages")

    # step 2 — chunk text
    print("Chunking text...")
    text_chunks = chunker(text_doc)
    print(f"Text chunks: {len(text_chunks)}")

    # step 3 — process images (cached)
    if os.path.exists(EXTRACTED_IMAGES):
        print("Loading cached image descriptions...")
        with open(EXTRACTED_IMAGES, "rb") as f:
            processed_images = pickle.load(f)
        print(f"Loaded {len(processed_images)} cached image descriptions.")
    else:
        print("Processing images via GPT-4o vision...")
        processed_images = image_processor(image_doc)

    # step 4 — chunk image descriptions
    print("Chunking image descriptions...")
    image_chunks = chunker(processed_images)
    print(f"Image chunks: {len(image_chunks)}")

    # step 5 — store in vector DB
    print("Storing in ChromaDB...")
    vector_store(text_chunks, TEXT_COLLECTION, rebuild=args.rebuild)
    if table_doc:
        vector_store(table_doc, TABLE_COLLECTION, rebuild=False)
    else:
        print("No tables found, skipping table collection.")  # no real tables, store as-is
    vector_store(image_chunks, IMAGE_COLLECTION, rebuild=args.rebuild)

    print("Ingestion complete.")

if __name__ == "__main__":
    main()