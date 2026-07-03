import base64
import pickle
import hashlib
import time
from config.settings import LLM_MODEL, client, EXTRACTED_IMAGES

MAX_RETRIES = 3
BASE_DELAY = 5  # seconds, doubles each retry


def _call_vision(image_data):
    """Single GPT-4o vision call with retry/backoff for transient failures
    (timeouts, rate limits, etc). Raises the last error if all attempts fail."""
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
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
            return response.choices[0].message.content
        except Exception as e:
            last_err = e
            print(f"    attempt {attempt}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(BASE_DELAY * (2 ** (attempt - 1)))
    raise last_err


def image_processor(image_doc):
    seen_hashes = {}  # image_hash -> caption, so duplicates reuse the real caption instead of the path
    failed_paths = []

    for i, img in enumerate(image_doc):
        try:
            with open(img.page_content, "rb") as f:
                raw_bytes = f.read()
                image_hash = hashlib.md5(raw_bytes).hexdigest()
                if image_hash in seen_hashes:
                    cached_caption = seen_hashes[image_hash]
                    if cached_caption:
                        img.page_content = cached_caption
                        print(f"Reusing caption for duplicate image on page {img.metadata['page_number']}")
                    else:
                        # first occurrence never got a real caption either — leave as failed
                        failed_paths.append(img.metadata.get("image_path", img.page_content))
                    continue
                image_data = base64.b64encode(raw_bytes).decode("utf-8")

            description = _call_vision(image_data)
            img.page_content = description
            seen_hashes[image_hash] = description
            print(f"Processing {i+1}/{len(image_doc)}: {img.metadata['page_number']}")
            if (i + 1) % 10 == 0:
                with open(EXTRACTED_IMAGES, "wb") as f:
                    pickle.dump(image_doc, f)
                print(f"Progress saved at {i+1}/{len(image_doc)}")
        except Exception as e:
            print(f"Skipped {img.page_content}: {e}")
            failed_paths.append(img.metadata.get("image_path", img.page_content))
            continue

    with open(EXTRACTED_IMAGES, "wb") as f:
        pickle.dump(image_doc, f)

    if failed_paths:
        print(f"\n{len(failed_paths)} image(s) still failed after {MAX_RETRIES} retries each:")
        for p in failed_paths:
            print(f"  {p}")
        print("These were left with path-as-content and should be reprocessed "
              "(see scripts/reprocess_broken_captions.py) rather than silently ingested as captions.")

    return image_doc