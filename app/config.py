import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "text-embedding-3-small"
)
