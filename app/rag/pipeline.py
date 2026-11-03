
import re

from app.rag.retriever import search_knowledge
from app.rag.generator import generate_answer


OUT_OF_SCOPE_PATTERNS = (
    r"\bviết\s+(?:giúp\s+)?(?:tôi\s+)?(?:một\s+)?bài\s+thơ\b",
    r"\b(?:trời|thời tiết)\b.*\bmưa\b",
    r"\btình trạng ví tiền\b",
    r"\b(?:đơn hàng|đơn)\s+(?:số\s+)?[a-z]{1,4}\d+\b",
    r"\bhoàn tiền\b.*\b(?:ngay|ngay lập tức)\b",
)

ABSTENTION_PATTERNS = (
    r"chưa có thông tin",
    r"không có thông tin",
    r"không tìm thấy thông tin",
    r"không thể xác định",
    r"không thể trả lời",
    r"chưa đủ thông tin",
    r"chưa xác định",
)


def is_out_of_scope(question: str) -> bool:
    normalized = question.casefold()
    return any(re.search(pattern, normalized) for pattern in OUT_OF_SCOPE_PATTERNS)


def is_abstention(answer: str) -> bool:
    normalized = answer.casefold()
    starts_with_abstention = any(
        re.match(pattern, normalized) for pattern in ABSTENTION_PATTERNS
    )
    contains_definitive_answer = bool(
        re.search(r"\d[\d.,]*\s*vnd|\bkhách hàng chịu\b|\borbit shop chịu\b", normalized)
    )
    return starts_with_abstention and not contains_definitive_answer


def run_rag(question: str, top_k: int = 3) -> dict:
    """
    Chạy toàn bộ RAG pipeline:
    1. Retrieve các chunks liên quan.
    2. Tạo context từ kết quả retrieval.
    3. Generate câu trả lời bằng LLM.
    """

    # 1. Từ chối sớm các yêu cầu không thuộc phạm vi hỗ trợ cửa hàng.
    if is_out_of_scope(question):
        return {
            "question": question,
            "answer": "Xin lỗi, yêu cầu này nằm ngoài phạm vi hỗ trợ của cửa hàng và tôi không thể thực hiện.",
            "sources": [],
            "abstained": True,
        }

    # 2. Retrieve
    try:
        matches = search_knowledge(question, top_k=top_k)
    except Exception as exc:
        return {
            "question": question,
            "answer": str(exc),
            "sources": [],
            "abstained": True,
        }

    # 3. Xử lý trường hợp không tìm thấy tài liệu
    if not matches:
        return {
            "question": question,
            "answer": "Xin lỗi, hiện tại tôi chưa tìm thấy thông tin liên quan để trả lời câu hỏi này.",
            "sources": [],
            "abstained": True,
        }

    # 4. Ghép các chunks thành context
    context_parts = []

    for match in matches:
        context_parts.append(
            f"[Nguồn: {match['source']}]\n{match['text']}"
        )

    context = "\n\n".join(context_parts)

    # 5. Generate answer
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

    # 6. Trả về kết quả
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
        "abstained": is_abstention(answer),
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
