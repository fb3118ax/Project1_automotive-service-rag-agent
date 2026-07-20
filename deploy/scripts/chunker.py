from langchain_text_splitters import RecursiveCharacterTextSplitter
from config.settings import CHUNK_SIZE, CHUNK_OVERLAP

# A chunk this much smaller than CHUNK_SIZE is treated as a leftover
# fragment (page header/footer/label) rather than real standalone content.
SMALL_CHUNK_RATIO = 0.5


def chunker(docs):
    if not docs:
        return []

    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks = splitter.split_documents(docs)
    threshold = CHUNK_SIZE * SMALL_CHUNK_RATIO

    # Pass 1: merge small trailing chunks backward into the previous chunk
    # on the same page (e.g. a footer label after real page content).
    merged = []
    for i, chunk in enumerate(chunks):
        content = chunk.page_content.strip()
        page = chunk.metadata.get("page_number")
        is_last_on_page = (
            i == len(chunks) - 1
            or chunks[i + 1].metadata.get("page_number") != page
        )
        same_page_as_prev = merged and merged[-1].metadata.get("page_number") == page

        if is_last_on_page and same_page_as_prev and len(content) < threshold:
            merged[-1].page_content = merged[-1].page_content.rstrip() + "\n" + content
        else:
            merged.append(chunk)

    # Pass 2: any chunk still small (e.g. the only/first chunk on its page,
    # with no same-page predecessor to merge into in pass 1) gets folded
    # forward into the next chunk instead — a lone heading belongs with the
    # content that follows it.
    final = []
    i = 0
    while i < len(merged):
        content = merged[i].page_content.strip()
        if len(content) < threshold and i + 1 < len(merged):
            merged[i + 1].page_content = content + "\n" + merged[i + 1].page_content.lstrip()
            i += 1
            continue
        final.append(merged[i])
        i += 1

    print(len(final))
    print(final[0].page_content)
    print(final[0].metadata)
    return final