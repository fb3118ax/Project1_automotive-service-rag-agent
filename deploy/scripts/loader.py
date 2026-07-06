import re
import os
import fitz  # PyMuPDF
from langchain_core.documents import Document
from config.settings import DATA_FOLDER


def clean_text(text):
    if not text:
        return None
    # remove footer
    text = re.sub(r'Online Edition for Part no\..*?II/\d+', '', text)
    # remove Seite X
    text = re.sub(r'Seite \d+', '', text)
    # before whitespace normalization
    text = re.sub(r'-\n', '', text)
    # remove standalone page numbers
    text = re.sub(r'^\d+$', '', text, flags=re.MULTILINE)
    # normalize whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def loader_doc():
    text_doc = []

    for file in os.listdir(DATA_FOLDER):
        if file.endswith(".pdf"):
            pdf_path = f"{DATA_FOLDER}/{file}"
            doc = fitz.open(pdf_path)

            for page_index in range(doc.page_count):
                page = doc[page_index]
                printed_page = page_index + 1  # 1-based, matches PDF page numbering

                if printed_page <= 3 or printed_page >= 460:
                    continue  # skip these pages

                # ── Text extraction ──
                texts = clean_text(page.get_text())
                if texts:
                    text_doc.append(Document(
                        page_content=texts,
                        metadata={
                            "page_number": printed_page,
                            "chunk_type": "text",
                            "source_file": file
                        }))

    return text_doc