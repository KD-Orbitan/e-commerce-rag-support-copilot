
import re
import csv
import logging
from pathlib import Path

from app.rag.retriever import search_knowledge
from app.rag.generator import generate_answer
from app.rag.router import classify_intent, normalize_question


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRODUCTS_PATH = PROJECT_ROOT / "data" / "products.csv"
logger = logging.getLogger(__name__)


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

    intent = classify_intent(question)

    if intent == "greeting":
        return {
            "question": question,
            "answer": "Xin chào! Mình có thể giúp bạn tìm hiểu sản phẩm, chính sách vận chuyển, thanh toán, đổi trả và các câu hỏi thường gặp của Orbit Shop.",
            "sources": [],
            "abstained": False,
        }

    if intent == "capability":
        return {
            "question": question,
            "answer": "Mình có thể hỗ trợ bạn tìm hiểu danh mục và thông tin sản phẩm, phí vận chuyển, phương thức thanh toán, chính sách đổi trả, bảo hành và các câu hỏi thường gặp của Orbit Shop.",
            "sources": [],
            "abstained": False,
        }

    if intent == "product_catalog":
        return format_product_catalog(question)

    # 2. Retrieve
    try:
        if intent == "product_search":
            matches = search_knowledge(
                question,
                top_k=top_k,
                source="products.csv",
            )
            if is_screen_mirroring_question(question):
                return generate_product_guidance(question, matches)
            return format_product_search(question, matches)
        matches = search_knowledge(question, top_k=top_k)
    except Exception as exc:
        logger.exception("Unexpected retrieval error for question: %s", question)
        return {
            "question": question,
            "answer": "Xin lỗi, hệ thống đang gặp sự cố khi truy xuất dữ liệu. Vui lòng thử lại sau.",
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
        logger.exception("Unexpected answer generation error for question: %s", question)
        return {
            "question": question,
            "answer": "Xin lỗi, hệ thống đang gặp sự cố khi tạo câu trả lời. Vui lòng thử lại sau.",
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


def load_products() -> list[dict]:
    with PRODUCTS_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def format_product_catalog(question: str) -> dict:
    products = load_products()
    lines = [
        f"{index}. {product['name']} - {product['category']} - "
        f"{format_vnd(product['price_vnd'])} VND"
        for index, product in enumerate(products, start=1)
    ]
    return {
        "question": question,
        "answer": "Orbit Shop hiện có các sản phẩm sau:\n" + "\n".join(lines),
        "sources": [
            {
                "id": product["id"],
                "source": "products.csv",
                "retrieval_type": "structured",
            }
            for product in products
        ],
        "abstained": False,
    }


def format_product_search(question: str, matches: list[dict]) -> dict:
    if not matches:
        return {
            "question": question,
            "answer": "Hiện tôi chưa tìm thấy sản phẩm phù hợp trong danh mục.",
            "sources": [],
            "abstained": True,
        }

    max_price = parse_max_price(question)

    product_lines = []
    proposed_matches = []
    for match in matches:
        metadata = match.get("metadata", match)
        name = metadata.get("name") or extract_document_field(match.get("text", ""), "Name")
        category = (
            metadata.get("category")
            or extract_document_field(match.get("text", ""), "Category", default="")
        )
        price = metadata.get("price_vnd")
        if price is None:
            price = extract_document_price(match.get("text", ""))
        if price is None:
            continue
        if max_price is not None and int(price) >= max_price:
            continue
        if not is_relevant_product_match(question, match):
            continue
        product_lines.append(
            f"- {name} ({category}), giá {format_vnd(price)} VND"
        )
        proposed_matches.append(match)

    if not product_lines:
        limit_text = (
            f" dưới {format_vnd(max_price)} VND"
            if max_price is not None
            else ""
        )
        return {
            "question": question,
            "answer": f"Dữ liệu cửa hàng hiện không ghi nhận sản phẩm phù hợp{limit_text}.",
            "sources": [],
            "abstained": True,
        }

    answer = "Sản phẩm phù hợp từ dữ liệu cửa hàng:\n" + "\n".join(product_lines)
    return {
        "question": question,
        "answer": answer,
        "sources": [
            {
                "id": match["id"],
                "source": match["source"],
                "distance": match["distance"],
            }
            for match in proposed_matches
        ],
        "abstained": False,
    }


def parse_max_price(question: str) -> int | None:
    normalized_ascii = normalize_question(question)
    price_match = re.search(
        r"(?:duoi|<)\s*([0-9]+(?:\.[0-9]{3})*)\s*(k|nghin|ngan)?"
        r"(?:\s*(?:vnd|dong|d))?",
        normalized_ascii,
    )
    if not price_match:
        return None

    amount_text = price_match.group(1)
    max_price = int(amount_text.replace(".", ""))
    if price_match.group(2) in {"k", "nghin", "ngan"}:
        max_price *= 1000
    return max_price


def format_vnd(price: str | int) -> str:
    return f"{int(price):,}".replace(",", ".")


def extract_document_field(text: str, field: str, default: str = "Sản phẩm") -> str:
    prefix = f"{field}:"
    for line in text.splitlines():
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip()
    return default


def extract_document_price(text: str) -> int | None:
    match = re.search(r"\b(?:Price:|Giá:)\s*([0-9]+)", text, re.IGNORECASE)
    return int(match.group(1)) if match else None


def is_relevant_product_match(question: str, match: dict) -> bool:
    metadata = match.get("metadata", match)
    text = match.get("text", "")
    name = str(metadata.get("name") or extract_document_field(text, "Name"))
    category = str(
        metadata.get("category")
        or extract_document_field(text, "Category", default="")
    )
    searchable = normalize_question(f"{name} {category} {text}")
    question_normalized = normalize_question(question)

    aliases = {
        "mouse": ("chuot", "mouse"),
        "keyboard": ("ban phim", "keyboard"),
        "headphones": ("tai nghe", "headphone", "headphones", "earbuds"),
        "accessories": ("phu kien", "accessories"),
    }

    camera_cover_terms = (
        "man che cam", "camera cover", "camera privacy cover",
        "webcam cover", "che camera", "che cam",
    )
    if any(term in question_normalized for term in camera_cover_terms):
        return False

    matched_aliases = [
        aliases[name]
        for name, aliases_for_group in (
            ("mouse", aliases["mouse"]),
            ("keyboard", aliases["keyboard"]),
            ("headphones", aliases["headphones"]),
            ("accessories", aliases["accessories"]),
        )
        if any(alias in question_normalized for alias in aliases_for_group)
    ]
    if matched_aliases:
        asks_about_laptop = bool(
            re.search(r"\b(?:laptop|may tinh|computer)\b", question_normalized)
        )
        if asks_about_laptop and any(
            "phu kien" in aliases or "accessories" in aliases
            for aliases in matched_aliases
        ):
            laptop_accessory_terms = (
                "laptop stand", "gia do laptop",
            )
            return any(term in searchable for term in laptop_accessory_terms)
        return any(alias in searchable for aliases in matched_aliases for alias in aliases)

    # Generic laptop/device words are not enough evidence for a product match.
    if re.search(r"\b(?:laptop|may tinh|computer|device|thiet bi)\b", question_normalized):
        specific_product_terms = (
            "laptop stand", "gia do laptop", "usb-c hub",
            "usb c hub", "usb-c cable", "usb c cable",
        )
        return any(term in searchable for term in specific_product_terms)

    meaningful_words = [
        word for word in re.findall(r"[a-z0-9]+", question_normalized)
        if len(word) >= 3 and word not in {
            "cho", "khong", "shop", "san", "pham", "duoi", "tren",
            "dang", "ban", "mua", "tim", "toi", "nay", "day", "voi",
            "laptop", "may", "tinh", "computer", "device", "thiet", "bi",
        }
    ]
    if not meaningful_words:
        return False

    product_terms = re.findall(r"[a-z0-9]+", searchable)
    return any(
        word in product_terms and word in {
            normalize_question(name_part)
            for name_part in re.findall(r"[a-z0-9]+", name, re.IGNORECASE)
        }
        for word in meaningful_words
    )
    return False


def is_screen_mirroring_question(question: str) -> bool:
    normalized = normalize_question(question)
    patterns = (
        r"\bchieu man hinh\b",
        r"\bphan chieu man hinh\b",
        r"\bcast(?:ing)? man hinh\b",
        r"\bscreen mirroring\b",
        r"\bmirror(?:ing)? phone screen\b",
        r"\bproject phone screen\b",
    )
    return any(re.search(pattern, normalized) for pattern in patterns)


def generate_product_guidance(question: str, matches: list[dict]) -> dict:
    if not matches:
        return {
            "question": question,
            "answer": "Không có thông tin xác nhận trong danh mục về thiết bị chiếu màn hình. Bạn đang dùng điện thoại Android hay iPhone?",
            "sources": [],
            "abstained": True,
        }

    context = "\n\n".join(
        f"[Nguồn: {match['source']}]\n{match['text']}"
        for match in matches
    )
    try:
        answer = generate_answer(question=question, context=context)
    except Exception as exc:
        logger.exception("Unexpected product guidance generation error for question: %s", question)
        return {
            "question": question,
            "answer": "Xin lỗi, hệ thống đang gặp sự cố khi tạo câu tư vấn. Vui lòng thử lại sau.",
            "sources": [],
            "abstained": True,
        }

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
