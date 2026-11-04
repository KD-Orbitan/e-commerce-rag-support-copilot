
import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from openai import OpenAI
from app.config import EMBEDDING_MODEL

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "chroma_db"
COLLECTION_NAME = "orbit_shop_knowledge"


def get_collection():
    chroma_client = chromadb.PersistentClient(path=str(DB_PATH))
    try:
        return chroma_client.get_collection(name=COLLECTION_NAME)
    except Exception as exc:
        raise ValueError(
            "Collection orbit_shop_knowledge chưa tồn tại. "
            "Hãy chạy ingest.ensure_index() trước."
        ) from exc


def get_distance_metric(collection) -> str:
    configuration = getattr(collection._model, "configuration_json", {})
    hnsw = configuration.get("hnsw", {})
    return hnsw.get("space", "unknown")


def search_knowledge(
    question: str,
    top_k: int = 3,
    source: str | None = None,
) -> list[dict]:
    """Tìm các chunks liên quan nhất đến câu hỏi."""

    load_dotenv()

    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("Không tìm thấy OPENAI_API_KEY trong file .env")

    if top_k < 1:
        raise ValueError("top_k phải lớn hơn hoặc bằng 1")

    # 1. Chuyển câu hỏi thành vector
    openai_client = OpenAI()

    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=question,
    )

    query_embedding = response.data[0].embedding

    # 2. Kết nối với ChromaDB đã tạo trong ingest.py
    collection = get_collection()

    total_chunks = collection.count()

    if total_chunks == 0:
        return []

    # 3. Tìm các vector gần nhất
    if source:
        source_ids = collection.get(where={"source": source}, include=[]).get("ids", [])
        result_count = len(source_ids)
    else:
        result_count = total_chunks

    if result_count == 0:
        return []

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(max(top_k, result_count), result_count),
        include=["documents", "metadatas", "distances"],
        where={"source": source} if source else None,
    )

    # 4. Chuyển kết quả thành danh sách dễ sử dụng
    matches = []

    for i in range(len(results["ids"][0])):
        matches.append({
            "id": results["ids"][0][i],
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "source": results["metadatas"][0][i].get("source"),
            "distance": results["distances"][0][i],
        })

    return matches


if __name__ == "__main__":
    question = "Tôi muốn thanh toán bằng crypto thì sao?"

    matches = search_knowledge(question, top_k=3)

    print(f"Question: {question}")
    print(f"Retrieved chunks: {len(matches)}")

    for rank, match in enumerate(matches, start=1):
        print(f"\n--- Result {rank} ---")
        print(f"ID: {match['id']}")
        print(f"Source: {match['source']}")
        print(f"Distance: {match['distance']:.4f}")
        print(f"Content:\n{match['text']}")
