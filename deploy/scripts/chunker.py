from langchain_text_splitters import RecursiveCharacterTextSplitter
from config.settings import CHUNK_SIZE, CHUNK_OVERLAP


def chunker(docs):
    if not docs:
        return []

    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks = splitter.split_documents(docs)

    print(len(chunks))
    print(chunks[0].page_content)
    print(chunks[0].metadata)
    return chunks