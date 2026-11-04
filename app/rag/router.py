import json
import os
import re

from dotenv import load_dotenv
from openai import OpenAI

from app.config import LLM_MODEL


GREETING_PATTERNS = (
    r"^(?:hi|hello|hey|chao(?: ban)?|xin chao|helo)[.! ]*$",
    r"^he+l+o+[.! ]*$",
)

CAPABILITY_PATTERNS = (
    r"\b(?:ban )?(?:ho tro|giup) duoc gi\b",
    r"\bban co the (?:ho tro|giup) gi\b",
    r"\bban ho tro duoc gi\b",
    r"\bchatbot (?:nay )?lam duoc gi\b",
    r"\bkha nang cua ban\b",
    r"\bvay ban co the ho tro gi\b",
)

CATALOG_PATTERNS = (
    r"\b(?:shop|cua hang|orbit shop)\b.*\bban\b.*\b(?:gi|san pham|hang)\b",
    r"\bco nhung san pham nao\b",
    r"\bdanh sach (?:tat ca )?san pham\b",
    r"\b(?:shop )?ban nhung gi(?: nhi)?\b",
    r"\b(?:toan bo|tat ca).*?(?:hang|san pham).*?(?:dang ban|ban)\b",
    r"\bcho(?: toi)? xem toan bo hang dang ban\b",
)

POLICY_PATTERNS = (
    r"\b(?:van chuyen|shipping|giao hang|ship)\b",
    r"\b(?:thanh toan|payment|cod|the ngan hang)\b",
    r"\b(?:doi tra|hoan tien|bao hanh|warranty)\b",
    r"\b(?:faq|câu hỏi thường gặp)\b",
)


def normalize_question(question: str) -> str:
    normalized = re.sub(r"\s+", " ", question.casefold()).strip()
    normalized = normalized.replace("đ", "d")
    normalized = normalized.replace("Đ", "d")
    normalized = (
        normalized.replace("á", "a").replace("à", "a")
        .replace("ả", "a").replace("ã", "a").replace("ạ", "a")
        .replace("ă", "a").replace("ắ", "a").replace("ằ", "a")
        .replace("ẳ", "a").replace("ẵ", "a").replace("ặ", "a")
        .replace("ấ", "a").replace("ầ", "a").replace("ẩ", "a")
        .replace("ẫ", "a").replace("ậ", "a")
        .replace("é", "e").replace("è", "e").replace("ẻ", "e")
        .replace("ẽ", "e").replace("ẹ", "e").replace("ế", "e")
        .replace("ề", "e").replace("ể", "e").replace("ễ", "e").replace("ệ", "e")
        .replace("ê", "e").replace("ề", "e").replace("ể", "e")
        .replace("ễ", "e").replace("ệ", "e")
        .replace("í", "i").replace("ì", "i").replace("ỉ", "i")
        .replace("ĩ", "i").replace("ị", "i")
        .replace("ó", "o").replace("ò", "o").replace("ỏ", "o")
        .replace("õ", "o").replace("ọ", "o").replace("ố", "o")
        .replace("ồ", "o").replace("ổ", "o").replace("ỗ", "o").replace("ộ", "o")
        .replace("ớ", "o").replace("ờ", "o").replace("ở", "o")
        .replace("ỡ", "o").replace("ợ", "o")
        .replace("ú", "u").replace("ù", "u").replace("ủ", "u")
        .replace("ũ", "u").replace("ụ", "u").replace("ứ", "u")
        .replace("ừ", "u").replace("ử", "u").replace("ữ", "u").replace("ự", "u")
        .replace("ư", "u").replace("ứ", "u").replace("ừ", "u")
        .replace("ử", "u").replace("ữ", "u").replace("ự", "u")
        .replace("ý", "y").replace("ỳ", "y").replace("ỷ", "y")
        .replace("ỹ", "y").replace("ỵ", "y")
    )
    return normalized


def classify_intent(question: str) -> str:
    normalized = normalize_question(question)

    if any(re.search(pattern, normalized) for pattern in GREETING_PATTERNS):
        return "greeting"
    if any(re.search(pattern, normalized) for pattern in CAPABILITY_PATTERNS):
        return "capability"
    if any(re.search(pattern, normalized) for pattern in CATALOG_PATTERNS):
        return "product_catalog"

    if should_use_policy_rules(normalized):
        return "store_policy"
    if classify_product_rule(normalized):
        return "product_search"

    return classify_with_llm_fallback(normalized)


def should_use_policy_rules(question: str) -> bool:
    has_policy = any(re.search(pattern, question) for pattern in POLICY_PATTERNS)
    return has_policy and classify_product_rule(question) is None


def classify_product_rule(question: str) -> str | None:
    screen_mirroring_pattern = (
        r"\b(?:chieu man hinh|phan chieu man hinh|cast man hinh|"
        r"screen mirroring|mirror(?:ing)? phone screen|project phone screen)\b"
    )
    if re.search(screen_mirroring_pattern, question):
        return "product_search"

    product_pattern = (
        r"\b(?:phu kien|chuot|ban phim|tai nghe|headphone|earbuds|webcam|"
        r"ssd|laptop stand|usb-c|man che cam|camera|den man hinh|"
        r"san pham|thiet bi|man hinh)\b"
    )
    search_pattern = (
        r"\b(?:tìm|tim|mua|xem|co|co ban|bán|ban|cần|can|thiết bị|thiet bi)\b"
    )
    if re.search(product_pattern, question) and re.search(search_pattern, question):
        return "product_search"
    return None


def classify_with_llm_fallback(question: str) -> str:
    try:
        raw_output = request_llm_classification(question)
        return parse_classifier_output(raw_output)["intent"]
    except Exception:
        return "general"


def request_llm_classification(question: str) -> str:
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY")

    response = OpenAI(api_key=api_key).chat.completions.create(
        model=LLM_MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Classify the customer question into exactly one intent: "
                    "product_search, store_policy, or general. Return only JSON "
                    "with keys intent and confidence. Confidence is from 0 to 1."
                ),
            },
            {"role": "user", "content": question},
        ],
    )
    return response.choices[0].message.content


def parse_classifier_output(raw_output: str, threshold: float | None = None) -> dict:
    try:
        payload = json.loads(raw_output)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("Classifier output is not valid JSON") from exc

    intent = payload.get("intent")
    confidence = payload.get("confidence")
    if intent not in {"product_search", "store_policy", "general"}:
        raise ValueError("Classifier returned an unsupported intent")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise ValueError("Classifier confidence must be a number")

    confidence = float(confidence)
    if not 0 <= confidence <= 1:
        raise ValueError("Classifier confidence must be between 0 and 1")

    if threshold is None:
        threshold = float(os.getenv("ROUTER_CONFIDENCE_THRESHOLD", "0.6"))
    if confidence < threshold:
        return {"intent": "general", "confidence": confidence}
    return {"intent": intent, "confidence": confidence}
