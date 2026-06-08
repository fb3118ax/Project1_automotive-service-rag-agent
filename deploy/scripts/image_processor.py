import base64
import pickle
import hashlib
from config.settings import LLM_MODEL, client, EXTRACTED_IMAGES



def image_processor(image_doc):
    seen_hashes = set()
    for i, img in enumerate(image_doc):
        try:
            with open(img.page_content, "rb") as f:
                raw_bytes = f.read()
                image_hash = hashlib.md5(raw_bytes).hexdigest()
                if image_hash in seen_hashes:
                    print(f"Skipping duplicate image on page {img.metadata['page_number']}")
                    continue
                seen_hashes.add(image_hash)
                image_data = base64.b64encode(raw_bytes).decode("utf-8")              

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
                                }
                            },
                            {
                                "type": "text",
                                "text": """You are analyzing a BMW service manual image, be specific and technical so the description is useful for a technician 
                                searching for information. look for any numbers, labels and text, what that images shows, check for symbols and indicators."""
                            }
                        ]
                    }
                ]
                )
            
            description = response.choices[0].message.content
            img.page_content = description
            print(f"Processing {i+1}/{len(image_doc)}: {img.metadata['page_number']}") #  progress counter inside the loop
            if (i + 1) % 10 == 0:
                with open(EXTRACTED_IMAGES, "wb") as f:
                    pickle.dump(image_doc, f)
                print(f"Progress saved at {i+1}/{len(image_doc)}")
        except Exception as e:
            print(f"Skipped {img.page_content}: {e}")
            continue
    
    with open(EXTRACTED_IMAGES, "wb") as f:
        pickle.dump(image_doc, f)
    return image_doc