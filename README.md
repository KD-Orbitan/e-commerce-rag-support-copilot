---
title: Orbit Shop RAG Support Copilot
emoji: 🛍️
colorFrom: blue
colorTo: indigo
sdk: gradio
app_file: app.py
pinned: false
---

# Orbit Shop RAG Support Copilot

Orbit Shop là một trợ lý hỗ trợ khách hàng bằng tiếng Việt, sử dụng Retrieval-Augmented
Generation (RAG) để trả lời từ tài liệu cửa hàng thay vì tự suy đoán chính sách.

## Mục tiêu và use case

- Trả lời câu hỏi về thanh toán, giao hàng, đổi trả và sản phẩm.
- Trích dẫn đúng chunk tài liệu đã truy xuất.
- Từ chối câu hỏi không có dữ liệu hoặc nằm ngoài phạm vi cửa hàng.
- Hỗ trợ thử nghiệm qua API FastAPI và giao diện chat Gradio.

## Kiến trúc

```text
Giao diện Gradio
      |
      v
POST /chat (FastAPI) hoặc app.py (Gradio Space)
      |
      v
RAG pipeline -> từ chối ngoài phạm vi -> vector retrieval -> OpenAI generation
      |                                           |
      |                                           v
      |                                   ChromaDB + chunks
      v
Câu trả lời + nguồn tài liệu + trạng thái abstained
```

- `data/`: tài liệu Markdown, catalog sản phẩm và bộ đánh giá.
- `app/rag/ingest.py`: đọc tài liệu, chia chunk, tạo embedding và lưu ChromaDB.
- `app/rag/retriever.py`: embedding câu hỏi và truy xuất top-k chunk.
- `app/rag/generator.py`: sinh câu trả lời có căn cứ bằng OpenAI.
- `app/rag/pipeline.py`: điều phối retrieval, citatation và abstention.
- `evaluation/`: đo retrieval và chạy đánh giá trực tiếp qua API.

## Chạy local

Yêu cầu Python 3.11 trở lên.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
copy .env.example .env
```

Điền khóa API của bạn trong `.env`:

```dotenv
OPENAI_API_KEY=your-openai-api-key
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
```

Chạy giao diện Gradio trực tiếp (không cần chạy API riêng):

```powershell
python app.py
```

Hoặc tạo index và chạy API riêng cho local development:

```powershell
python -m app.rag.ingest
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Mở terminal thứ hai:

```powershell
python app/ui.py
```

- API docs: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`
- Demo Gradio: `http://127.0.0.1:7860`

Ví dụ gọi API:

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/chat" `
  -ContentType "application/json" `
  -Body '{"question":"Đơn 300.000 VND thì phí giao hàng tiêu chuẩn là bao nhiêu?","top_k":3}'
```

## Kiểm thử

```powershell
python -m pytest tests/test_core.py -q
python evaluation/evaluate_retrieve.py
```

Để đánh giá API trực tiếp, khởi động API, sau đó chạy:

```powershell
python evaluation/run_live_evaluation.py
```

Kết quả Day 3 được lưu tại [evaluation/results/summary.md](evaluation/results/summary.md)
và [evaluation/results/live_evaluation.md](evaluation/results/live_evaluation.md).

## Kết quả đánh giá

| Cấu hình | Recall@chunk | Recall@source | MRR |
|---|---:|---:|---:|
| Baseline, top_k=3 | 100% (20/20) | 100% (20/20) | 0.8167 |
| Experiment, top_k=5 | 100% (20/20) | 100% (20/20) | 0.8167 |

Bộ live có 30 câu hỏi; rerun Day 3 đạt 100% correctness trên bản API hiện tại.
Groundedness/citation và giới hạn từng trường hợp được ghi chi tiết trong báo cáo
Day 3.

## Deploy Hugging Face Spaces

1. Tạo Space mới với SDK `Gradio`.
2. Giữ `ZeroGPU` ở chế độ không bắt buộc; OpenAI API không yêu cầu GPU.
3. Upload source, dữ liệu và `requirements.txt`; không cần Dockerfile cho Space này.
4. Thêm `OPENAI_API_KEY` vào Space Secrets; cấu hình `LLM_MODEL` và
   `EMBEDDING_MODEL` trong Variables nếu muốn ghi đè giá trị mặc định.
5. Build Space và kiểm tra cả câu có đáp án lẫn câu không có đáp án.

Không commit khóa API hoặc file `.env`. Không có URL demo placeholder trong README này.

## Giới hạn

- Dữ liệu mẫu nhỏ và không đại diện cho mọi đơn hàng hoặc chính sách sản phẩm.
- Độ chính xác phụ thuộc vào chất lượng retrieval, model embedding và khả năng
  của nhà cung cấp LLM.
- Demo không tra cứu đơn hàng thật; mã đơn hàng chỉ được dùng để kiểm tra abstention.
- Một lần Space restart có thể mất cache/persistent data; ứng dụng chủ động
  nạp lại tài liệu để xử lý trường hợp này.
