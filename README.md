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
POST /chat (FastAPI)
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

Tạo hoặc làm mới index rồi khởi động API và giao diện:

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

## Docker

Docker Space sẽ tạo lại vector index từ `data/` tại thời điểm container khởi động,
nên không phụ thuộc vào dữ liệu ChromaDB của máy local.

```powershell
docker build -t orbit-shop-rag .
docker run --rm -p 7860:7860 `
  -e OPENAI_API_KEY="your-openai-api-key" `
  -e LLM_MODEL="gpt-4o-mini" `
  -e EMBEDDING_MODEL="text-embedding-3-small" `
  orbit-shop-rag
```

Kiểm tra container:

```powershell
Invoke-RestMethod http://127.0.0.1:7860/
Invoke-RestMethod http://127.0.0.1:8000/health
```

## Deploy Hugging Face Spaces

1. Tạo Space mới với SDK `Docker`.
2. Đặt `EXPOSE 7860`/app port là `7860` trong cấu hình Space.
3. Upload source, dữ liệu, `requirements.txt` và Dockerfile.
4. Thêm `OPENAI_API_KEY`, `LLM_MODEL` và `EMBEDDING_MODEL` vào Space Secrets.
5. Build Space và kiểm tra cả câu có đáp án lẫn câu không có đáp án.

Không commit khóa API hoặc file `.env`. Demo online chính thức: `Chưa deploy; hãy
thay bằng URL Space sau khi hoàn tất build`.

## Giới hạn

- Dữ liệu mẫu nhỏ và không đại diện cho mọi đơn hàng hoặc chính sách sản phẩm.
- Độ chính xác phụ thuộc vào chất lượng retrieval, model embedding và khả năng
  của nhà cung cấp LLM.
- Demo không tra cứu đơn hàng thật; mã đơn hàng chỉ được dùng để kiểm tra abstention.
- Một lần restart Docker có thể mất cache/persistent data; entrypoint chủ động
  nạp lại tài liệu để xử lý trường hợp này.
