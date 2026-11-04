import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.rag import pipeline
from app.rag import generator
from app.rag.ingest import split_into_chunks
from app.rag.router import (
    classify_intent,
    parse_classifier_output,
    request_llm_classification,
)


client = TestClient(app)


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_invalid_chat_request():
    response = client.post("/chat", json={"question": "", "top_k": 3})

    assert response.status_code == 422


def test_pipeline_abstains_when_retrieval_has_no_results(monkeypatch):
    monkeypatch.setattr(pipeline, "search_knowledge", lambda question, top_k: [])

    result = pipeline.run_rag("Một chính sách không có trong dữ liệu")

    assert result["abstained"] is True
    assert result["sources"] == []
    assert "chưa tìm thấy thông tin" in result["answer"].lower()


def test_pipeline_marks_textual_abstention(monkeypatch):
    matches = [{
        "id": "faq_006",
        "text": "Các phương thức thanh toán được công khai trong tài liệu.",
        "source": "faq.md",
        "distance": 0.4,
    }]
    monkeypatch.setattr(pipeline, "search_knowledge", lambda question, top_k: matches)
    monkeypatch.setattr(
        pipeline,
        "generate_answer",
        lambda question, context: "Không có thông tin xác nhận về Ethereum.",
    )

    result = pipeline.run_rag("Shop có nhận Ethereum không?")

    assert result["abstained"] is True
    assert result["sources"][0]["id"] == "faq_006"


def test_pipeline_rejects_out_of_scope_request(monkeypatch):
    monkeypatch.setattr(
        pipeline,
        "search_knowledge",
        lambda question, top_k: pytest.fail("Không được truy xuất ngoài phạm vi"),
    )

    result = pipeline.run_rag("Bạn viết giúp tôi một bài thơ về tình yêu được không?")

    assert result["abstained"] is True
    assert result["sources"] == []


def test_chunking_preserves_small_sections():
    text = "## Thanh toán\n\nChấp nhận COD và thẻ ngân hàng."

    chunks = split_into_chunks(text, chunk_size=800, overlap=0)

    assert len(chunks) == 1
    assert "Chấp nhận COD" in chunks[0]


def test_missing_api_key_has_clear_error(monkeypatch):
    monkeypatch.setattr(generator, "OPENAI_API_KEY", None)

    with pytest.raises(RuntimeError, match="thiếu OPENAI_API_KEY"):
        generator.generate_answer("Xin chào", "Ngữ cảnh kiểm thử")


@pytest.mark.parametrize(
    ("question", "intent"),
    [
        ("Hellooo", "greeting"),
        ("Vậy bạn có thể hỗ trợ gì cho tôi?", "capability"),
        ("Orbit Shop có bán những sản phẩm gì?", "product_catalog"),
        ("Shop có chuột không dây dưới 300.000đ không?", "product_search"),
        ("Tôi muốn mua thiết bị để chiếu màn hình điện thoại lên máy tính", "product_search"),
        ("Phí vận chuyển là bao nhiêu?", "store_policy"),
        ("Hôm nay trời Hà Nội có mưa không?", "general"),
        ("hêllo", "greeting"),
        ("Chào bạn", "greeting"),
        ("Bạn hỗ trợ được gì?", "capability"),
        ("Shop bán những gì nhỉ?", "product_catalog"),
        ("Cho tôi xem toàn bộ hàng đang bán", "product_catalog"),
        ("Có phụ kiện nào cho laptop không?", "product_search"),
        ("Shop có bán màn che cam laptop không?", "product_search"),
        ("Shop có hỗ trợ thanh toán COD không?", "store_policy"),
        (
            "Tôi muốn xem phim từ điện thoại trên laptop bằng thiết bị gì? Shop có bán không?",
            "product_search",
        ),
    ],
)
def test_query_routing(question, intent):
    assert classify_intent(question) == intent


@pytest.mark.parametrize(
    "question",
    [
        "screen mirroring from phone to laptop",
        "mirror phone screen to laptop",
        "project phone screen to laptop",
    ],
)
def test_screen_mirroring_questions_use_real_product_search_router(question):
    assert classify_intent(question) == "product_search"


def test_greeting_and_capability_do_not_embed(monkeypatch):
    monkeypatch.setattr(
        pipeline,
        "search_knowledge",
        lambda *args, **kwargs: pytest.fail("Không được truy xuất"),
    )

    greeting = pipeline.run_rag("Hellooo")
    capability = pipeline.run_rag("Vậy bạn có thể hỗ trợ gì cho tôi?")

    assert greeting["abstained"] is False
    assert capability["abstained"] is False


def test_catalog_returns_all_ten_products():
    result = pipeline.run_rag("Orbit Shop có bán những sản phẩm gì?")

    assert len(pipeline.load_products()) == 10
    assert len(result["sources"]) == 10
    assert "Wireless Mouse" in result["answer"]
    assert "250.000 VND" in result["answer"]


def test_product_search_uses_source_filter_and_price(monkeypatch):
    def fake_search(question, top_k, source=None):
        assert source == "products.csv"
        return [{
            "id": "P001",
            "text": "Name: Wireless Mouse\nPrice: 250000 VND",
            "metadata": {
                "source": "products.csv",
                "name": "Wireless Mouse",
                "category": "Accessories",
                "price_vnd": 250000,
            },
            "source": "products.csv",
            "distance": 0.2,
        }]

    monkeypatch.setattr(pipeline, "search_knowledge", fake_search)
    result = pipeline.run_rag("Shop có chuột không dây dưới 300.000đ không?")

    assert "Wireless Mouse" in result["answer"]
    assert "250.000 VND" in result["answer"]
    assert result["sources"][0]["source"] == "products.csv"


def test_policy_query_uses_rag_and_preserves_citation(monkeypatch):
    monkeypatch.setattr(
        pipeline,
        "search_knowledge",
        lambda question, top_k: [{
            "id": "shipping_001",
            "text": "Phí vận chuyển tiêu chuẩn là 30.000 VND.",
            "metadata": {"source": "shipping.md"},
            "source": "shipping.md",
            "distance": 0.3,
        }],
    )
    monkeypatch.setattr(
        pipeline,
        "generate_answer",
        lambda question, context: "Phí vận chuyển tiêu chuẩn là 30.000 VND.",
    )

    result = pipeline.run_rag("Phí vận chuyển là bao nhiêu?")

    assert result["sources"][0]["id"] == "shipping_001"
    assert result["sources"][0]["source"] == "shipping.md"


def test_mirroring_question_uses_documented_capabilities_only(monkeypatch):
    monkeypatch.setattr(
        pipeline,
        "search_knowledge",
        lambda question, top_k, source: [{
            "id": "P009",
            "text": "USB-C Cable hỗ trợ sạc và truyền dữ liệu.",
            "metadata": {"source": "products.csv"},
            "source": "products.csv",
            "distance": 0.4,
        }],
    )
    observed = {}

    def fake_generate(question, context):
        observed["context"] = context
        return "Không có thông tin xác nhận cáp USB-C hỗ trợ chiếu màn hình. Bạn dùng Android hay iPhone?"

    monkeypatch.setattr(pipeline, "generate_answer", fake_generate)
    result = pipeline.run_rag(
        "Tôi muốn mua thiết bị để chiếu màn hình điện thoại lên máy tính"
    )

    assert "trần dữ liệu" in observed["context"] or "truyền dữ liệu" in observed["context"]
    assert "Không có thông tin xác nhận" in result["answer"]
    assert "Android hay iPhone" in result["answer"]


def test_llm_classifier_fallback(monkeypatch):
    assert parse_classifier_output(
        '{"intent": "product_search", "confidence": 0.92}'
    )["intent"] == "product_search"


def test_llm_classifier_low_confidence_defaults_to_general():
    assert parse_classifier_output(
        '{"intent": "store_policy", "confidence": 0.2}',
        threshold=0.6,
    )["intent"] == "general"


def test_llm_classifier_invalid_json_defaults_to_general(monkeypatch):
    monkeypatch.setattr(
        "app.rag.router.request_llm_classification",
        lambda question: "not json",
    )

    from app.rag import router

    assert router.classify_with_llm_fallback("Câu hỏi chưa phân loại") == "general"


def test_llm_classifier_api_error_defaults_to_general(monkeypatch):
    def fail(question):
        raise RuntimeError("API unavailable")

    monkeypatch.setattr(
        "app.rag.router.request_llm_classification",
        fail,
    )

    from app.rag import router

    assert router.classify_with_llm_fallback("Câu hỏi chưa phân loại") == "general"


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Tôi muốn chiếu màn hình điện thoại lên laptop", True),
        ("Phản chiếu màn hình từ điện thoại sang máy tính", True),
        ("Shop hỗ trợ cast màn hình không?", True),
        ("Thiết bị nào hỗ trợ screen mirroring?", True),
        ("mirror phone screen to my laptop", True),
        ("project phone screen to laptop", True),
        ("Bàn phím cơ có đèn không?", False),
    ],
)
def test_screen_mirroring_detection(question, expected):
    assert pipeline.is_screen_mirroring_question(question) is expected


@pytest.mark.parametrize(
    ("question", "expected_price"),
    [
        ("Chuột không dây dưới 300.000đ", 300000),
        ("Chuột không dây dưới 300k", 300000),
        ("Chuột không dây dưới 1.000.000 VND", 1000000),
    ],
)
def test_product_price_limit_parsing(question, expected_price):
    assert pipeline.parse_max_price(question) == expected_price


def test_no_product_under_price_returns_no_sources():
    matches = [{
        "id": "P006",
        "text": "Name: Portable SSD 1TB\nCategory: Storage\nPrice: 1750000 VND",
        "metadata": {
            "source": "products.csv",
            "name": "Portable SSD 1TB",
            "category": "Storage",
            "price_vnd": 1750000,
        },
        "source": "products.csv",
        "distance": 0.2,
    }]

    result = pipeline.format_product_search(
        "Ổ cứng dưới 300.000đ",
        matches,
    )

    assert result["abstained"] is True
    assert result["sources"] == []


def test_citations_only_include_product_matches_not_filtered_products():
    matches = [
        {
            "id": "P001",
            "text": "Name: Wireless Mouse\nCategory: Accessories\nPrice: 250000 VND",
            "metadata": {
                "source": "products.csv",
                "name": "Wireless Mouse",
                "category": "Accessories",
                "price_vnd": 250000,
            },
            "source": "products.csv",
            "distance": 0.2,
        },
        {
            "id": "P006",
            "text": "Name: Portable SSD 1TB\nCategory: Storage\nPrice: 1750000 VND",
            "metadata": {
                "source": "products.csv",
                "name": "Portable SSD 1TB",
                "category": "Storage",
                "price_vnd": 1750000,
            },
            "source": "products.csv",
            "distance": 0.5,
        },
    ]

    result = pipeline.format_product_search(
        "Chuột không dây dưới 300.000đ",
        matches,
    )

    assert [source["id"] for source in result["sources"]] == ["P001"]


def test_irrelevant_vector_result_is_not_proposed(monkeypatch):
    monkeypatch.setattr(
        pipeline,
        "search_knowledge",
        lambda question, top_k, source=None: [{
            "id": "P006",
            "text": "Name: Portable SSD 1TB\nCategory: Storage\nPrice: 1750000 VND",
            "metadata": {
                "source": "products.csv",
                "name": "Portable SSD 1TB",
                "category": "Storage",
                "price_vnd": 1750000,
            },
            "source": "products.csv",
            "distance": 2.5,
        }],
    )

    result = pipeline.run_rag("Bạn có chuột không dây không?")

    assert result["abstained"] is True
    assert result["sources"] == []


def test_retrieval_api_error_is_not_exposed(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("api-key=secret technical stack details")

    monkeypatch.setattr(pipeline, "search_knowledge", fail)

    result = pipeline.run_rag("Shop có chuột không dây không?")

    assert "secret" not in result["answer"]
    assert "technical" not in result["answer"]
    assert result["abstained"] is True


@pytest.mark.parametrize(
    "question",
    [
        "Chiếu màn hình điện thoại lên laptop",
        "Phản chiếu màn hình",
        "Cast màn hình từ điện thoại sang laptop",
        "screen mirroring from phone to laptop",
        "mirror phone screen to laptop",
        "project phone screen to laptop",
    ],
)
def test_screen_mirroring_variants_use_guidance(monkeypatch, question):
    monkeypatch.setattr(pipeline, "classify_intent", lambda text: "product_search")
    monkeypatch.setattr(
        pipeline,
        "search_knowledge",
        lambda question, top_k, source=None: [{
            "id": "P009",
            "text": "USB-C Cable hỗ trợ sạc và truyền dữ liệu.",
            "metadata": {
                "source": "products.csv",
                "name": "USB-C Cable",
                "category": "Cables",
                "price_vnd": 120000,
            },
            "source": "products.csv",
            "distance": 0.4,
        }],
    )
    monkeypatch.setattr(
        pipeline,
        "generate_answer",
        lambda question, context: (
            "Không có thông tin xác nhận sản phẩm hỗ trợ chiếu màn hình. "
            "USB-C Cable được ghi nhận hỗ trợ sạc và truyền dữ liệu."
        ),
    )

    result = pipeline.run_rag(question)

    assert "Không có thông tin xác nhận" in result["answer"]
    assert "AirPlay" not in result["answer"]
    assert "Miracast" not in result["answer"]
    assert "HDMI" not in result["answer"]


@pytest.mark.parametrize(
    ("question", "expected_names"),
    [
        ("Shop có tai nghe không?", {"Office Headphones", "Wireless Earbuds"}),
        ("Bạn có bàn phím cơ không?", {"Mechanical Keyboard"}),
    ],
)
def test_product_alias_groups_match_relevant_products(question, expected_names):
    matches = []
    for product in pipeline.load_products():
        matches.append({
            "id": product["id"],
            "text": (
                f"Name: {product['name']}\n"
                f"Category: {product['category']}\n"
                f"Price: {product['price_vnd']} VND"
            ),
            "metadata": {"source": "products.csv", "price_vnd": int(product["price_vnd"])},
            "source": "products.csv",
            "distance": 0.3,
        })

    matched_names = {
        pipeline.extract_document_field(match["text"], "Name")
        for match in matches
        if pipeline.is_relevant_product_match(question, match)
    }

    assert matched_names == expected_names


def test_laptop_accessory_query_does_not_match_generic_laptop_overlap():
    webcam = {
        "id": "P005",
        "text": "Name: Webcam HD\nCategory: Accessories\nDescription: Webcam độ phân giải HD",
        "metadata": {"source": "products.csv"},
        "source": "products.csv",
        "distance": 0.3,
    }

    assert not pipeline.is_relevant_product_match(
        "Có phụ kiện nào cho laptop không?",
        webcam,
    )


def test_camera_cover_query_does_not_match_webcam_as_camera_cover():
    webcam = {
        "id": "P005",
        "text": "Name: Webcam HD\nCategory: Accessories\nDescription: Webcam độ phân giải HD",
        "metadata": {"source": "products.csv"},
        "source": "products.csv",
        "distance": 0.3,
    }

    assert not pipeline.is_relevant_product_match(
        "Shop có bán màn che cam laptop không?",
        webcam,
    )


def test_category_falls_back_to_product_document():
    match = {
        "id": "P005",
        "text": (
            "Name: Webcam HD\n"
            "Category: Accessories\n"
            "Price: 390000 VND"
        ),
        "metadata": {"source": "products.csv", "price_vnd": 390000},
        "source": "products.csv",
        "distance": 0.3,
    }

    result = pipeline.format_product_search("Bạn có webcam không?", [match])

    assert result["abstained"] is False
    assert "Webcam HD (Accessories)" in result["answer"]
