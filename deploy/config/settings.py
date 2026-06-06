import chromadb
import os
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ── API ────────────────────────────────────────────────────────────────────────
api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI()

# ── LLM ───────────────────────────────────────────────────────────────────────
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")

# ── Embedding ─────────────────────────────────────────────────────────────────
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# ── ChromaDB ──────────────────────────────────────────────────────────────────
DB_PATH = os.getenv("CHROMA_DB_PATH", "./BMW_RAG_db")
TEXT_COLLECTION = os.getenv("TEXT_COLLECTION", "text_chunks")
TABLE_COLLECTION = os.getenv("TABLE_COLLECTION", "table_chunks")

# ── Retrieval ─────────────────────────────────────────────────────────────────
RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", "5"))

# ── Confidence ────────────────────────────────────────────────────────────────
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))

# ── Conversation ──────────────────────────────────────────────────────────────
OWNER_MAX_WORDS = int(os.getenv("OWNER_MAX_WORDS", "150"))

# ── Clients ───────────────────────────────────────────────────────────────────
embedding_model = OpenAIEmbeddings(model=EMBEDDING_MODEL)
client_db = chromadb.PersistentClient(path=DB_PATH)

text_store = Chroma(
    client=client_db,
    collection_name=TEXT_COLLECTION,
    embedding_function=embedding_model
)

table_store = Chroma(
    client=client_db,
    collection_name=TABLE_COLLECTION,
    embedding_function=embedding_model
)

# ── PATTERNS ───────────────────────────────────────────────────────────────────
INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore all instructions",
    "you are now",
    "forget your instructions",
    "disregard your instructions"]