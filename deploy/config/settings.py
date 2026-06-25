import os
from langchain_openai import OpenAIEmbeddings
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

# ── Retrieval ─────────────────────────────────────────────────────────────────
RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", "4"))

# ── Confidence ────────────────────────────────────────────────────────────────
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))

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
CHUNK_SIZE = 2000
CHUNK_OVERLAP = 200

# ── EXTRACTED_IMAGES ───────────────────────────────────────────────────────────────────
EXTRACTED_IMAGES = "processed_images.pkl"

# ── EXTRACTED_IMAGES_DESCRIPTION_COLLECTION ──────────────────────────────────────────
IMAGE_COLLECTION = os.getenv("IMAGE_COLLECTION", "image_chunks")

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
    "weather", "recipe", "sports", "movie", "music"
]