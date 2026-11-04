---
title: Orbit Shop RAG Support Copilot
emoji: "\U0001F6CD\U0000FE0F"
colorFrom: blue
colorTo: indigo
sdk: gradio
app_file: app.py
pinned: false
---

# Orbit Shop RAG Support Copilot

Orbit Shop is a Vietnamese customer-support copilot built around
Retrieval-Augmented Generation (RAG). It answers from store Markdown policies
and a structured product catalog while distinguishing documented facts from
unsupported assumptions.

## Overview and use cases

- Product discovery from the current `products.csv` catalog.
- Shipping, payment, returns, warranty, and FAQ policy questions.
- Grounded answers with source citations and abstention behavior.
- Out-of-scope request handling.
- FastAPI, Gradio, and Streamlit interfaces.

## Implemented features

- Hybrid intent routing: deterministic rules for clear intents plus a
  confidence-controlled OpenAI fallback for ambiguous intents.
- Structured full-catalog lookup without vector search.
- Source-filtered product retrieval from ChromaDB.
- Chunk/source citations and abstention for retrieved answers.
- Product metadata including ID, name, category, and price.
- Source fingerprint and embedding-model checks before index reuse.
- Conservative generation prompts that discourage unsupported product claims.
- Unit tests for routing, fallback behavior, pipeline boundaries, citations,
  and documented product facts.

## Technology stack

- Python
- OpenAI embeddings and chat completions
- ChromaDB
- FastAPI and Pydantic
- Gradio and Streamlit
- pytest

## Architecture

```text
User question
      |
      v
Intent router
  |-- greeting / capability / product catalog rules
  |-- policy / product rules
  `-- JSON LLM fallback with confidence validation
      |
      +--> Direct greeting/capability response
      |
      +--> Structured CSV catalog lookup
      |
      +--> Product vector retrieval with source = products.csv
      |
      `--> Policy/general vector retrieval
                  |
                  v
          Embedding -> ChromaDB top-k chunks -> grounded generation
                                                        |
                                                        v
                                        Answer + citations + abstention
```

## RAG pipeline

1. Markdown policies and `products.csv` are loaded in `app/rag/ingest.py`.
2. Markdown is split into heading-aware chunks; each CSV product becomes one
   document.
3. Text chunks are embedded with the configured embedding model.
4. ChromaDB stores vectors, documents, IDs, and source/product metadata.
5. Rule-based routing handles clear greeting, capability, catalog, policy,
   and sufficiently specific product-search queries without an LLM call.
6. Ambiguous remaining intents use the configured chat model, with a JSON
   schema, supported-intent validation, confidence validation, and safe
   fallback to `general`.
7. Policy and general questions use normal vector retrieval. Individual
   product searches are restricted to `products.csv`.
8. Retrieved chunks become generation context; supporting IDs, sources, and
   retrieval distances are returned with the answer.

### Structured product lookup

Full-catalog questions read `data/products.csv` directly. This avoids using
top-k vector search to answer "list everything". These entries are
structured-source citations, not vector results, and therefore do not display
fake `0.0000` distances.

Vector distance is not interpreted as a similarity percentage. The current
Chroma configuration must be evaluated before adding any relevance threshold.
To propose an evidence-based threshold, run retrieval questions with known
expected product IDs and compare the distance distributions for correct and
incorrect results at several `top_k` values. Keep the threshold separate by
source/model and report precision@k plus recall@k; do not choose a threshold
from a few subjective examples.

## Project structure

```text
app/
  main.py                 FastAPI application
  schemas.py              API request/response models
  rag/
    router.py             Rule-based and LLM intent routing
    pipeline.py           Routing and retrieval orchestration
    retriever.py          ChromaDB vector retrieval
    generator.py          Grounded answer generation
    ingest.py             Indexing and source consistency
data/
  products.csv            Structured product source
  *.md                    Store policy sources
  evaluation.json         Retrieval/evaluation cases
evaluation/
  evaluate_retrieve.py    Retrieval quality experiment
  run_live_evaluation.py  API-level live evaluation
tests/
  test_core.py            Unit and integration tests
app.py                    Gradio application
streamlit_app.py          Streamlit application
```

## Local setup

Python 3.11 or newer is recommended.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
copy .env.example .env
```

Configure API access in `.env`. Do not commit real secrets.

```dotenv
OPENAI_API_KEY=your-openai-api-key
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
ROUTER_CONFIDENCE_THRESHOLD=0.6
```

Start Gradio:

```powershell
python app.py
```

Start Streamlit:

```powershell
streamlit run streamlit_app.py
```

Create/reuse the index and start FastAPI:

```powershell
python -m app.rag.ingest
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

API documentation:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/health`
- Gradio local demo: `http://127.0.0.1:7860`

Example API request:

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/chat" `
  -ContentType "application/json" `
  -Body '{"question":"Đơn 300.000 VND thì phí giao hàng tiêu chuẩn là bao nhiêu?","top_k":3}'
```

## Tests

```powershell
python -m pytest -q
python -m compileall -q app
python -m pip check
```

Tests use mocks for OpenAI generation/classification where appropriate and do
not require a real API call for normal unit-test execution.

## Evaluation

Run retrieval evaluation from the project root:

```powershell
python -m evaluation.evaluate_retrieve
```

Run live API evaluation after starting FastAPI:

```powershell
python evaluation/run_live_evaluation.py
```

Existing artifacts are stored in `evaluation/results/`. Because source data,
chunking, embeddings, and prompts affect measured quality, rerun evaluation
after those changes rather than treating historical figures as current.

## Measured results

The retrieval evaluation was run on 2026-11-03 using the current Chroma index
and `data/evaluation.json`.

| Metric | Result |
|---|---:|
| Questions | 30 |
| Answerable questions | 20 |
| Recall@3 by chunk | 100% (20/20) |
| Recall@3 by source | 100% (20/20) |
| MRR@3 | 0.8167 |
| Direct / multi-hop / paraphrase | 100% / 100% / 100% |

These figures measure retrieval only. Generation correctness, groundedness,
and live deployment behavior require separate live evaluation and human review.
Historical artifacts are also preserved under `evaluation/results/`, including
[summary.md](evaluation/results/summary.md). Rerun the experiment after source,
chunking, embedding-model, or index changes.

## Hugging Face Spaces deployment

1. Create a new Gradio Space.
2. Upload the source, data, and `requirements.txt`.
3. Add `OPENAI_API_KEY` under Space Secrets.
4. Configure `LLM_MODEL` and `EMBEDDING_MODEL` only if you need overrides.
5. Test answerable, product, abstention, and out-of-scope questions.

## Streamlit Community Cloud deployment

1. Do not commit `.env`, API keys, generated secrets, or temporary indexes.
2. Set the Streamlit entry point to `streamlit_app.py`.
3. In **App settings > Secrets**, add:

```toml
OPENAI_API_KEY = "your-openai-api-key"
LLM_MODEL = "gpt-4o-mini"
EMBEDDING_MODEL = "text-embedding-3-small"
ROUTER_CONFIDENCE_THRESHOLD = "0.6"
```

Streamlit secrets map into the environment variables used by the application.
On a fresh cloud filesystem, the app runs `ensure_index()` and creates the
Chroma index from `data/`. Ephemeral storage may be reset by restart or
redeploy.

## Limitations and future improvements

- The sample policy and product data is limited.
- The demo cannot look up real orders or perform transactions/refunds.
- Questions with multiple independent demands are not fully orchestrated.
  Mixed product/policy requests are handled conservatively rather than with
  speculative product or policy claims.
- Product capabilities are limited to facts present in `products.csv`.
- A relevance threshold is intentionally not configured without measured data.
- Classifier failures safely fall back to `general`; the classifier is not
  used to assert that a product exists.
- Persistent cloud storage availability depends on the chosen deployment
  platform.
