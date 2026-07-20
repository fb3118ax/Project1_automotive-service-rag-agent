import os
from langchain_openai import OpenAIEmbeddings
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
# Source manual PDF, rasterized on demand by the recaption scripts to read
# numbered-callout legends visually. Override via the PDF_PATH env var.
PDF_PATH = os.getenv(
    "PDF_PATH",
    "C:/Users/Pranali Jadhav/OneDrive/Documents/GEN_AI/my_study/Bot_Project_1/bmw_manual.pdf",
)

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

# ── Sementic cache ──────────────────────────────────────────────────────────────────
CACHE_DB_PATH            = os.getenv("CACHE_DB_PATH", "./mechai_cache_db")
CACHE_COLLECTION         = os.getenv("CACHE_COLLECTION", "semantic_cache")
CACHE_SIMILARITY_THRESHOLD = float(os.getenv("CACHE_SIMILARITY_THRESHOLD", "0.95"))
CACHE_TTL_DAYS           = int(os.getenv("CACHE_TTL_DAYS", "30"))

# ── Retrieval ─────────────────────────────────────────────────────────────────
RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", "4"))

# Chunks below this many characters are treated as near-empty (bare section
# headers like "Notes\nNOTES", stray page fragments) and excluded from
# retrieval candidates before they can occupy a top-K slot or dilute confidence.
MIN_CHUNK_CHARS = int(os.getenv("MIN_CHUNK_CHARS", "40"))

# ── Confidence ────────────────────────────────────────────────────────────────
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.4"))

# ── Conversation ──────────────────────────────────────────────────────────────
OWNER_MAX_WORDS = int(os.getenv("OWNER_MAX_WORDS", "150"))

# ── Clients ───────────────────────────────────────────────────────────────────
embedding_model = OpenAIEmbeddings(model=EMBEDDING_MODEL)

# ── PATTERNS ───────────────────────────────────────────────────────────────────
INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore all instructions",
    "you are now",
    "forget your instructions",
    "disregard your instructions"]

# ── SOURCE_PDFS ───────────────────────────────────────────────────────────────────
DATA_FOLDER = os.getenv("DATA_FOLDER", "./data")

# ── CHUNKS ───────────────────────────────────────────────────────────────────
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

# ── TOKEN_LIMIT ───────────────────────────────────────────────────────────────────
TOKEN_LIMIT = 20000

# ── QUERY_VARIATIONS ───────────────────────────────────────────────────────────────────
QUERY_VARIATIONS_LIMIT = 2

# ── GREETINGS ───────────────────────────────────────────────────────────────────
GREETINGS = {"hi", "hello", "hey", "howdy", "hiya", "sup", "good morning", "good evening", "good afternoon"}

# ── OFF TOPIC KEYWORDS ───────────────────────────────────────────────────────────────────
OFF_TOPIC_KEYWORDS = [
    "joke", "riddle", "funny", "stock price", "share price",
    "how much does", "buy a bmw", "dealer", "dealership",
    "weather", "recipe", "sports", "movie", "music", "bomb"
]

# ── Demo login credentials (UI-gate only, not real auth) ──────────────────
DEMO_CREDENTIALS = {
    "owner": {"username": "owner", "password": "owner123"},
    "technician": {"username": "technician", "password": "tech123"},
}

MAX_LOGIN_ATTEMPTS = 3
LOCKOUT_SECONDS = 60  # 2.5 min

# ── Cosmos DB (lazy init) ──────────────────────────────────────────────────
COSMOS_CONNECTION_STRING = os.getenv("COSMOS_CONNECTION_STRING")
COSMOS_DATABASE          = "mechai-db"

SESSIONS_CONTAINER  = "sessions"
QUERYLOG_CONTAINER  = "query_log"

SESSION_TTL_SECONDS   = 1296000  # 15 days
QUERYLOG_TTL_SECONDS  = 1296000  # 15 days

FAQ_MIN_COUNT = 3
FAQ_SLOTS = 5

# ── Near-duplicate filtering ───────────────────────────────────────────────
NEAR_DUP_OVERLAP_THRESHOLD = 0.7