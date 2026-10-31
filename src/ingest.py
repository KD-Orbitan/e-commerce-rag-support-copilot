import csv
from pathlib import Path
import os
from dotenv import load_dotenv
from openai import OpenAI
import chromadb
import re

# Xác định thư mục gốc của project
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT/"data"


def load_markdown(file_path: Path)->str:
    """Đọc nội dung một file Markdown."""
    return file_path.read_text(encoding="utf-8")


def load_products(file_path: Path) -> list[str]:
    """Đọc CSV và chuyển mỗi sản phẩm thành một document riêng."""
    products = []

    with file_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        for product in reader:
            text = (
                f"Product ID: {product['id']}\n"
                f"Name: {product['name']}\n"
                f"Category: {product['category']}\n"
                f"Price: {product['price_vnd']} VND\n"
                f"Description: {product['description']}"
            )
            products.append(text)

    return products



def load_documents() -> list[dict]:
    """Đọc các nguồn dữ liệu và trả về danh sách documents."""
    documents = []

    markdown_files = [
        "shipping.md",
        "returns.md",
        "payment.md",
        "faq.md",
    ]

    for filename in markdown_files:
        content = load_markdown(DATA_DIR / filename)
        documents.append({
            "source": filename,
            "content": content,
        })

    product_texts = load_products(DATA_DIR / "products.csv")

    for product_text in product_texts:
        # Lấy Product ID để nhận diện document ổn định.
        product_id = next(
            line.split(": ", 1)[1]
            for line in product_text.splitlines()
            if line.startswith("Product ID:")
        )

        documents.append({
            "source": "products.csv",
            "content": product_text,
            "document_id": product_id,
        })

    return documents






def split_into_chunks(
    text: str,
    chunk_size: int = 800,
    overlap: int = 120,
) -> list[str]:
    """Chia văn bản theo tiêu đề, sau đó theo đoạn văn."""

    if chunk_size <= 0:
        raise ValueError("chunk_size phải lớn hơn 0")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "overlap phải từ 0 đến nhỏ hơn chunk_size"
        )

    # Tách trước theo các tiêu đề Markdown cấp 2.
    sections = re.split(r"(?m)(?=^## )", text.strip())

    chunks = []

    for section in sections:
        section = section.strip()
        if not section:
            continue

        # Ghép các đoạn văn trong cùng một mục nếu còn vừa giới hạn.
        paragraphs = [
            p.strip()
            for p in section.split("\n\n")
            if p.strip()
        ]

        current = ""

        for paragraph in paragraphs:
            # Nếu một đoạn quá dài, chia riêng với overlap.
            if len(paragraph) > chunk_size:
                if current:
                    chunks.append(current)
                    current = ""

                start = 0
                while start < len(paragraph):
                    end = min(start + chunk_size, len(paragraph))
                    part = paragraph[start:end].strip()

                    if part:
                        chunks.append(part)

                    if end == len(paragraph):
                        break

                    start = end - overlap

                continue

            candidate = (
                f"{current}\n\n{paragraph}"
                if current
                else paragraph
            )

            if len(candidate) <= chunk_size:
                current = candidate
            else:
                if current:
                    chunks.append(current)

                current = paragraph

        if current:
            chunks.append(current)

    return chunks



def create_chunks(documents: list[dict]) -> list[dict]:
    """Chia tài liệu thành chunks và gắn ID, metadata."""
    chunks = []

    for doc in documents:
        source = doc["source"]
        text = doc["content"]

        # Sản phẩm đã là document riêng, không cần chia nhỏ.
        if source == "products.csv":
            chunk_id = doc["document_id"]
            text_parts = [text]
        else:
            text_parts = split_into_chunks(text)

        for index, part in enumerate(text_parts):
            if source == "products.csv":
                chunk_id = doc["document_id"]
            else:
                chunk_id = f"{Path(source).stem}_{index:03d}"

            chunks.append({
                "id": chunk_id,
                "source": source,
                "text": part,
            })

    return chunks



def embed_and_store(chunks: list[dict]) -> None:
    """Tạo embeddings cho chunks và lưu vào ChromaDB."""
    load_dotenv()

    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("Không tìm thấy OPENAI_API_KEY trong file .env")

    openai_client = OpenAI()

    # Bước 1: Gửi nội dung chunks đến OpenAI Embeddings API
    texts = [chunk["text"] for chunk in chunks]

    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=texts,
    )

    # Bảo đảm vector đúng thứ tự tương ứng với chunks
    embeddings = [
        item.embedding
        for item in sorted(response.data, key=lambda item: item.index)
    ]

    # Bước 2: Tạo hoặc mở database lưu trữ trên máy
    chroma_client = chromadb.PersistentClient(
        path=str(PROJECT_ROOT / "chroma_db")
    )

    collection = chroma_client.get_or_create_collection(
        name="orbit_shop_knowledge"
    )

    # Bước 3: Lưu nội dung, vector và metadata
    collection.upsert(
        ids=[chunk["id"] for chunk in chunks],
        documents=texts,
        embeddings=embeddings,
        metadatas=[
            {"source": chunk["source"]}
            for chunk in chunks
        ],
    )

    print(f"Embeddings created: {len(embeddings)}")
    print(f"Vectors stored: {collection.count()}")
    print(f"Database path: {PROJECT_ROOT / 'chroma_db'}")
    print(f"Tokens used: {response.usage.total_tokens}")






if __name__ == "__main__":
    documents = load_documents()
    chunks = create_chunks(documents)

    print(f"Documents: {len(documents)}")
    print(f"Chunks: {len(chunks)}")

    # product_chunks = [
    #     chunk for chunk in chunks
    #     if chunk["source"] == "products.csv"
    # ]
    # print(f"Product chunks: {len(product_chunks)}")


    # shipping_text = load_markdown(DATA_DIR / "shipping.md")
    # shipping_chunks = split_into_chunks(shipping_text)

    # print("\n=== SHIPPING CHUNKS ===")
    # for index, chunk in enumerate(shipping_chunks):
    #     print(f"\n--- Chunk {index} ({len(chunk)} chars) ---")
    #     print(chunk[:400])

    # Tạo embeddings và lưu dữ liệu vào ChromaDB.
    embed_and_store(chunks)


