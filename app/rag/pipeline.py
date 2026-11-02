
from app.rag.retriever import search_knowledge
from app.rag.generator import generate_answer


def run_rag(question: str, top_k: int = 3) -> dict:
    """
    Chạy toàn bộ RAG pipeline:
    1. Retrieve các chunks liên quan.
    2. Tạo context từ kết quả retrieval.
    3. Generate câu trả lời bằng LLM.
    """

    # 1. Retrieve
    try:
        matches = search_knowledge(question, top_k=top_k)
    except Exception as exc:
        return {
            "question": question,
            "answer": str(exc),
            "sources": [],
            "abstained": True,
        }

    # 2. Xử lý trường hợp không tìm thấy tài liệu
    if not matches:
        return {
            "question": question,
            "answer": "Xin lỗi, hiện tại tôi chưa tìm thấy thông tin liên quan để trả lời câu hỏi này.",
            "sources": [],
            "abstained": True,
        }

    # 3. Ghép các chunks thành context
    context_parts = []

    for match in matches:
        context_parts.append(
            f"[Nguồn: {match['source']}]\n{match['text']}"
        )

    context = "\n\n".join(context_parts)

    # 4. Generate answer
    try:
        answer = generate_answer(
            question=question,
            context=context,
        )
    except Exception as exc:
        return {
            "question": question,
            "answer": str(exc),
            "sources": [
                {
                    "id": match["id"],
                    "source": match["source"],
                    "distance": match["distance"],
                }
                for match in matches
            ],
            "abstained": True,
        }

    # 5. Trả về kết quả
    sources = [
        {
            "id": match["id"],
            "source": match["source"],
            "distance": match["distance"],
        }
        for match in matches
    ]

    return {
        "question": question,
        "answer": answer,
        "sources": sources,
        "abstained": False,
    }


if __name__ == "__main__":
    # question = "Tôi muốn thanh toán bằng crypto thì sao?"
    question = "Cửa hàng có hỗ trợ thanh toán Bitcoin không?"

    result = run_rag(question)

    print(f"Question: {result['question']}")
    print(f"\nAnswer: {result['answer']}")

    print("\nRetrieved sources:")

    for source in result["sources"]:
        print(
            f"- {source['source']} "
            f"(distance: {source['distance']:.4f})"
        )
