
import re
import pdfplumber
import os
from langchain_core.documents import Document
from PIL import Image
from io import BytesIO
import shutil
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
    table_doc =[]
    image_doc = []

    for file in os.listdir(DATA_FOLDER):
        if file.endswith(".pdf"):
            # file_name = file.replace(".pdf", "")
            with pdfplumber.open(f"{DATA_FOLDER}/{file}") as pdf:
                
                if os.path.exists("images"):
                    shutil.rmtree("images")                
                os.makedirs("images", exist_ok=True)
                for page in pdf.pages:
                    if page.page_number <= 21 or page.page_number >= 460:
                        continue  # skip these pages
                    texts = clean_text(page.extract_text())
                    if texts:
                        text_doc.append(Document(
                                page_content=texts,
                                    metadata={
                                        "page_number": page.page_number,
                                        # "section": f"page_{page.page_number}",
                                        "chunk_type": "text",
                                        "source_file": file
                                        # "image_path": {image_path} # image only
                                        }))
                                    
                    tables = page.extract_tables()
                    for i, table in enumerate(tables):
                        table_doc.append(Document(
                                page_content=str(table),
                                    metadata={
                                        "page_number": page.page_number,
                                        # "section": f"page_{page.page_number}",
                                        "chunk_type": "table",
                                        "source_file": file
                                        # "image_path": {image_path} # image only
                                        }
                                    ))
                    images = [img for img in page.images if img["srcsize"][0] >= 100 and img["srcsize"][1] >= 100]                        
                    for i, img in enumerate(images):
                        try:
                            raw_bytes = img["stream"].get_data()
                            pil_image = Image.open(BytesIO(raw_bytes))
                            if pil_image.mode == "CMYK":
                                pil_image = pil_image.convert("RGB")
                            image_path = f"images/page_{page.page_number}_image_{i}.png"
                            pil_image.save(image_path)
                            image_doc.append(Document(
                                    page_content=f"images/page_{page.page_number}_image_{i}.png",
                                    metadata={
                                        "page_number": page.page_number,
                                        # "section": f"page_{page.page_number}",
                                        "chunk_type": "image_description",
                                        "source_file": file,
                                        "image_path": image_path # image for only
                                        }))
                        except Exception as e:
                            print(f"Skipped image on page {page.page_number}: {e}")
                            continue

    return text_doc, table_doc, image_doc
                        
    