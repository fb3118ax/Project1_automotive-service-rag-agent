import chromadb
import os
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from openai import OpenAI
# import pickle
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# Now you can access your variables using os.environ
api_key = os.environ.get("OPENAI_API_KEY")
DB_PATH = os.getenv("CHROMA_DB_PATH", "./BMW_RAG_db")
client = OpenAI()
embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
client_db = chromadb.PersistentClient(path=DB_PATH)
text_store = Chroma(
    client=client_db,
    collection_name="text_chunks",
    embedding_function=embedding_model
)

table_store = Chroma(
    client=client_db,
    collection_name="table_chunks",
    embedding_function=embedding_model
)