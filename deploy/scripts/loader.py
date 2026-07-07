import re
import os
import fitz  # PyMuPDF
from langchain_core.documents import Document
from config.settings import DATA_FOLDER


def clean_text(text, printed_page=None):
    """
    printed_page: the actual 1-based page number being cleaned. Used to
    strip ONLY the real footer page number line, not any digit-only line.

    BUG FIXED: the old blanket regex r'^\d+$' stripped every standalone
    digit-only line, not just the footer. Numbered legend items (e.g. the
    17-item "Around the steering wheel" legend on page 36) render their
    item markers as standalone lines in PyMuPDF's linear text extraction
    ("1", "2", "3", "4", "5", each on its own line, directly above their
    description). The blanket regex silently deleted every one of those
    markers along with the real footer number, so retrieved chunks lost
    all item numbering for any legend using this layout — confirmed via
    raw doc[35].get_text() dump on page 36: standalone "1".."5" lines each
    immediately preceding their item description, plus the real footer
    "36" at the very end. Now we only strip a standalone line that matches
    this specific page's printed number.
    """
    if not text:
        return None
    # remove footer
    text = re.sub(r'Online Edition for Part no\..*?II/\d+', '', text)
    # remove Seite X
    text = re.sub(r'Seite \d+', '', text)
    # before whitespace normalization
    text = re.sub(r'-\n', '', text)
    # remove ONLY the real footer page number line (not any digit-only line —
    # legend item markers like "1", "2", "3" are also standalone digit lines
    # and must be preserved)
    if printed_page is not None:
        text = re.sub(rf'(?m)^\s*{printed_page}\s*$', '', text)
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
                texts = clean_text(page.get_text(), printed_page=printed_page)
                if texts:
                    text_doc.append(Document(
                        page_content=texts,
                        metadata={
                            "page_number": printed_page,
                            "chunk_type": "text",
                            "source_file": file
                        }))

    return text_doc