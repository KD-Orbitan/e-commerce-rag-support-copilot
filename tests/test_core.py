import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.rag import pipeline
from app.rag import generator
from app.rag.ingest import split_into_chunks


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
