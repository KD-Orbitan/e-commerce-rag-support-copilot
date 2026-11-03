import os
from pathlib import Path

# HF Spaces loads this file as the application entrypoint. Mark the root file
# as a package-compatible module so existing imports such as app.main still work.
__path__ = [str(Path(__file__).resolve().parent / "app")]

import gradio as gr
from dotenv import load_dotenv

from app.rag.ingest import ensure_index
from app.rag.pipeline import run_rag


load_dotenv()


def initialize_app() -> str:
    try:
        return ensure_index()
    except Exception as exc:
        return f"Không thể khởi tạo dữ liệu: {type(exc).__name__}"


INDEX_STATUS = initialize_app()


def format_sources(sources: list[dict]) -> str:
    if not sources:
        return "Không có tài liệu được trích dẫn."

    lines = [
        f"- {source['source']} "
        f"(chunk: `{source['id']}`, distance: {source['distance']:.4f})"
        for source in sources
    ]
    return "\n".join(lines)


def respond(message: str, history: list):
    question = message.strip()
    if not question:
        return history, "Bạn hãy nhập câu hỏi.", "Không có nguồn.", "Không xác định"

    history = list(history or [])
    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": "Đang xử lý..."})
    yield history, "Đang truy xuất tài liệu...", "", "Đang xử lý"

    if not os.getenv("OPENAI_API_KEY"):
        history[-1]["content"] = (
            "Demo chưa được cấu hình API key. "
            "Vui lòng liên hệ quản trị viên."
        )
        yield history, "", "Không có nguồn.", "Có (thiếu cấu hình)"
        return

    try:
        result = run_rag(question=question, top_k=3)
        history[-1]["content"] = result["answer"]
        sources = format_sources(result["sources"])
        abstention = "Có" if result["abstained"] else "Không"
        yield history, "", sources, abstention
    except Exception as exc:
        history[-1]["content"] = (
            "Không thể xử lý câu hỏi do dịch vụ AI đang gặp sự cố."
        )
        yield history, "", "Không có nguồn.", "Có (lỗi dịch vụ)"


with gr.Blocks(title="Orbit Shop RAG Support Copilot") as demo:
    gr.Markdown(
        "# Orbit Shop - AI Support Copilot\n"
        "Trả lời dựa trên tài liệu hỗ trợ của cửa hàng."
    )
    gr.Markdown(INDEX_STATUS)

    chatbot = gr.Chatbot(height=420, label="Cuộc trò chuyện")
    question = gr.Textbox(
        label="Câu hỏi",
        placeholder="Ví dụ: Đơn 300.000 VND có được miễn phí giao hàng không?",
    )
    send = gr.Button("Gửi câu hỏi", variant="primary")

    with gr.Row():
        with gr.Column():
            status = gr.Markdown("Sẵn sàng")
        with gr.Column():
            gr.Markdown("### Từ chối câu hỏi")
            abstention = gr.Markdown("Không xác định")
            gr.Markdown("### Nguồn tài liệu")
            sources = gr.Markdown("Không có nguồn.")

    send.click(
        respond,
        inputs=[question, chatbot],
        outputs=[chatbot, status, sources, abstention],
    )
    question.submit(
        respond,
        inputs=[question, chatbot],
        outputs=[chatbot, status, sources, abstention],
    )

    gr.Examples(
        examples=[
            "Đơn hàng 600.000 VND có được miễn phí vận chuyển không?",
            "Shop có hỗ trợ thanh toán bằng crypto không?",
            "Tôi có thể đổi trả trong bao lâu?",
        ],
        inputs=question,
    )


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
