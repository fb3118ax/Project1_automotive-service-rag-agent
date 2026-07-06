import argparse
from scripts.loader import loader_doc
from scripts.chunker import chunker
from scripts.vector_store import vector_store
from config.settings import TEXT_COLLECTION

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild", action="store_true", help="Wipe and rebuild the vector DB")
    args = parser.parse_args()

    # step 1 — load and clean PDF
    print("Loading PDF...")
    text_doc = loader_doc()
    print(f"Loaded: {len(text_doc)} text pages")

    # step 2 — chunk text
    print("Chunking text...")
    text_chunks = chunker(text_doc)
    print(f"Text chunks: {len(text_chunks)}")

    # step 3 — store in vector DB
    print("Storing in ChromaDB...")
    vector_store(text_chunks, TEXT_COLLECTION, rebuild=args.rebuild)

    print("Ingestion complete.")

if __name__ == "__main__":
    main()