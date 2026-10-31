
import gradio as gr
import requests

API_URL = "http://127.0.0.1:8000/chat"


def respond(message, history):
    if not message.strip():
        return "Bạn hãy nhập câu hỏi nhé."

    try:
        response = requests.post(
            API_URL,
            json={
                "question": message,
                "top_k": 3,
            },
            timeout=60,
        )

        response.raise_for_status()
        result = response.json()

        answer = result["answer"]

        # Hiển thị nguồn tài liệu được truy xuất
        sources = result.get("sources", [])

        if sources:
            source_text = "\n".join(
                f"- {source['source']} "
                f"(distance: {source['distance']:.4f})"
                for source in sources
            )

            answer += f"\n\n**Nguồn tham khảo:**\n{source_text}"

        return answer

    except requests.exceptions.RequestException as e:
        return f"Không thể kết nối đến RAG API: {e}"


demo = gr.ChatInterface(
    fn=respond,
    title="Orbit Shop - AI Support Copilot",
    description="Trợ lý AI hỗ trợ khách hàng dựa trên tài liệu của Orbit Shop.",
    examples=[
        "Tôi có thể đổi trả trong bao lâu?",
        "Đơn hàng 600.000 VND có được miễn phí vận chuyển không?",
        "Shop có hỗ trợ thanh toán bằng crypto không?",
        "Tôi muốn hủy đơn hàng thì phải làm sao?",
    ],
)

if __name__ == "__main__":
    demo.launch()
