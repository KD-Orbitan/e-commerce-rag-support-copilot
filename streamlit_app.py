import os
import html

import streamlit as st
from dotenv import load_dotenv


load_dotenv()


def configure_secrets() -> None:
    for name in ("OPENAI_API_KEY", "LLM_MODEL", "EMBEDDING_MODEL"):
        if os.getenv(name):
            continue
        try:
            value = st.secrets[name]
        except (KeyError, FileNotFoundError):
            continue
        if value:
            os.environ[name] = str(value)


configure_secrets()

from app.rag.ingest import ensure_index
from app.rag.pipeline import run_rag


@st.cache_resource(show_spinner=False)
def initialize_index() -> str:
    return ensure_index()


st.set_page_config(
    page_title="E-commerce RAG | AI Support Copilot",
    page_icon="🛍️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_question" not in st.session_state:
    st.session_state.pending_question = ""


st.markdown(
    """
    <style>
    :root {
        --ink: #172033;
        --muted: #697386;
        --line: #e7eaf0;
        --soft: #f6f8fb;
        --accent: #4f46e5;
        --accent-soft: #eef2ff;
        --success: #16835b;
    }
    .stApp { background: #f8f9fc; color: var(--ink); }
    header[data-testid="stHeader"] {
        background: rgba(248,249,252,.92);
        border-bottom: 1px solid var(--line);
    }
    section[data-testid="stSidebar"] { display: none; }
    .block-container { max-width: 1120px !important; padding: 0 28px 32px !important; }
    .topbar {
        height: 72px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 24px;
        border-bottom: 1px solid var(--line);
        margin-bottom: 42px;
    }
    .brand { display: flex; align-items: center; gap: 12px; min-width: 0; }
    .brand-mark {
        width: 38px; height: 38px; border-radius: 10px;
        display: grid; place-items: center; color: white; font-weight: 700;
        background: var(--accent); box-shadow: 0 6px 16px rgba(79,70,229,.18);
    }
    .brand-name { font-size: 15px; font-weight: 700; line-height: 1.2; }
    .brand-subtitle { margin-top: 3px; color: var(--muted); font-size: 12px; }
    .top-actions { display: flex; align-items: center; gap: 16px; }
    .online {
        display: inline-flex; align-items: center; gap: 7px;
        color: var(--success); font-size: 13px; font-weight: 600; white-space: nowrap;
    }
    .online-dot {
        width: 7px; height: 7px; border-radius: 50%; background: #22c55e;
        box-shadow: 0 0 0 3px #dcfce7;
    }
    .header-link { color: #475569; font-size: 13px; font-weight: 600; text-decoration: none; }
    .header-link:hover { color: var(--accent); }
    .page-heading { margin-bottom: 24px; }
    .page-heading h1 {
        margin: 0; font-size: clamp(28px,4vw,38px); line-height: 1.15;
        letter-spacing: -.035em; color: var(--ink);
    }
    .page-heading p { margin: 9px 0 0; color: var(--muted); font-size: 16px; }
    .conversation-card {
        border: 1px solid var(--line); border-radius: 16px; background: white;
        box-shadow: 0 10px 30px rgba(15,23,42,.035); overflow: hidden;
    }
    div[data-testid="stChatMessage"] { max-width: 760px; margin: 0 auto; }
    div[data-testid="stChatMessageContent"] p { font-size: 15px; line-height: 1.68; }
    .empty-state { text-align: center; padding: 54px 24px 46px; }
    .empty-icon {
        width: 48px; height: 48px; margin: 0 auto 18px; border-radius: 13px;
        display: grid; place-items: center; color: var(--accent);
        background: var(--accent-soft); font-size: 22px; border: 1px solid #dfe4ff;
    }
    .empty-state h2 { margin: 0; font-size: 23px; letter-spacing: -.025em; }
    .empty-state p {
        max-width: 590px; margin: 10px auto 0; color: var(--muted);
        line-height: 1.65; font-size: 15px;
    }
    .suggestion-label {
        margin-top: 26px; color: #475569; font-size: 12px; font-weight: 700;
        letter-spacing: .04em; text-transform: uppercase;
    }
    div[data-testid="stChatInput"] { border-radius: 14px; margin-top: 16px; }
    div[data-testid="stChatInput"] textarea {
        min-height: 58px !important; border-radius: 14px !important;
        border: 1px solid #d7dce7 !important; padding: 18px 52px 18px 18px !important;
        font-size: 15px !important; box-shadow: 0 8px 24px rgba(15,23,42,.05);
    }
    div[data-testid="stChatInput"] textarea:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px rgba(79,70,229,.12) !important;
    }
    .source-panel {
        margin-top: 14px; border: 1px solid var(--line); border-radius: 12px;
        background: var(--soft); padding: 2px 14px;
    }
    .source-panel summary {
        cursor: pointer; padding: 11px 0; font-size: 13px; font-weight: 700; color: #334155;
    }
    .source-item { border-top: 1px solid var(--line); padding: 11px 0; min-width: 0; }
    .source-name { overflow-wrap: anywhere; font-size: 13px; font-weight: 700; color: #334155; }
    .source-meta { margin-top: 4px; color: var(--muted); font-size: 12px; }
    .abstention-card, .error-card { border-radius: 12px; padding: 14px 16px; margin-top: 4px; }
    .abstention-card { border: 1px solid #fde68a; background: #fffbeb; color: #78350f; }
    .error-card { border: 1px solid #fecaca; background: #fff7f7; color: #991b1b; }
    .state-title { font-weight: 700; margin-bottom: 4px; }
    div[data-testid="stButton"] button {
        border-radius: 9px; border-color: #dfe3eb; color: #475569;
        background: white; font-size: 13px; height: 36px; white-space: normal;
    }
    div[data-testid="stButton"] button:hover {
        border-color: #c7d2fe; color: var(--accent); background: #fafaff;
    }
    @media (max-width: 640px) {
        .block-container { padding: 0 14px 24px !important; }
        .topbar { height: 64px; margin-bottom: 28px; }
        .brand-mark { width: 34px; height: 34px; }
        .header-link { display: none; }
        .page-heading { margin-bottom: 18px; }
        .page-heading h1 { font-size: 29px; }
        .page-heading p { font-size: 14px; }
        .empty-state { padding: 38px 16px 34px; }
        .empty-state h2 { font-size: 21px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="topbar">
      <div class="brand">
        <div class="brand-mark">R</div>
        <div>
          <div class="brand-name">E-commerce RAG</div>
          <div class="brand-subtitle">AI Support Copilot</div>
        </div>
      </div>
      <div class="top-actions">
        <div class="online"><span class="online-dot"></span>Online</div>
        <a class="header-link" href="https://github.com/KD-Orbitan/e-commerce-rag-support-copilot"
           target="_blank" rel="noopener noreferrer">GitHub</a>
      </div>
    </div>
    <div class="page-heading">
      <h1>AI Support Copilot</h1>
      <p>Ask questions about our store, policies, and products.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.caption("Demo configuration is incomplete: OPENAI_API_KEY is not set.")
else:
    try:
        initialize_index()
    except Exception as exc:
        st.caption(f"Knowledge base unavailable: {type(exc).__name__}")


def process_question(question: str) -> None:
    question = question.strip()
    if not question:
        return
    st.session_state.messages.append({"role": "user", "content": question})
    with st.spinner("Searching store knowledge..."):
        try:
            result = run_rag(question=question, top_k=3)
            st.session_state.messages.append({
                "role": "assistant",
                "content": result["answer"],
                "sources": result.get("sources", []),
                "abstained": bool(result.get("abstained", False)),
            })
        except Exception:
            st.session_state.messages.append({
                "role": "assistant",
                "error": True,
                "failed_question": question,
            })
    st.rerun()


def retry_question(message_index: int, question: str) -> None:
    del st.session_state.messages[message_index]
    if (
        st.session_state.messages
        and st.session_state.messages[-1]["role"] == "user"
        and st.session_state.messages[-1]["content"] == question
    ):
        st.session_state.messages.pop()
    process_question(question)


if st.session_state.pending_question:
    pending = st.session_state.pending_question
    st.session_state.pending_question = ""
    process_question(pending)


if not st.session_state.messages:
    st.markdown(
        """
        <div class="conversation-card">
          <div class="empty-state">
            <div class="empty-icon">✦</div>
            <h2>E-commerce Support Copilot</h2>
            <p>Ask anything about products, shipping, returns, payments, and store policies.</p>
            <div class="suggestion-label">Suggested questions</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    suggestions = [
        ("What is the return policy?", "Returns"),
        ("How much is standard shipping?", "Shipping"),
        ("What payment methods are supported?", "Payment"),
        ("How long does delivery take?", "Delivery"),
    ]
    columns = st.columns(4)
    for column, (suggested, label) in zip(columns, suggestions):
        if column.button(label, key=f"suggest-{label}"):
            st.session_state.pending_question = suggested
            st.rerun()
else:
    clear_column, _ = st.columns([1, 5])
    if clear_column.button("Clear conversation", key="clear-conversation"):
        st.session_state.messages = []
        st.rerun()

    for index, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            if message.get("error"):
                st.markdown(
                    """
                    <div class="error-card">
                      <div class="state-title">Something went wrong</div>
                      Unable to process your request. Please try again.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button("Try again", key=f"retry-{index}-{message['failed_question']}"):
                    retry_question(index, message["failed_question"])
                continue

            st.markdown(message["content"])

            if message["role"] == "assistant" and message.get("abstained"):
                st.markdown(
                    """
                    <div class="abstention-card">
                      I couldn't find enough information in the store documents to answer this question.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            sources = message.get("sources", []) if message["role"] == "assistant" else []
            if sources:
                items = []
                for source in sources:
                    source_name = html.escape(str(source.get("source", "Unknown source")))
                    source_id = html.escape(str(source.get("id", "")))
                    meta = [f"chunk: {source_id}"]
                    distance = source.get("distance")
                    if distance is not None:
                        meta.append(f"distance: {float(distance):.4f}")
                    if source.get("retrieval_type") == "structured":
                        meta.append("structured data lookup")
                    items.append(
                        '<div class="source-item">'
                        f'<div class="source-name">▣ {source_name}</div>'
                        f'<div class="source-meta">{" · ".join(meta)}</div>'
                        "</div>"
                    )
                st.markdown(
                    '<details class="source-panel">'
                    f"<summary>{len(sources)} source{'s' if len(sources) != 1 else ''}</summary>"
                    f"{''.join(items)}"
                    "</details>",
                    unsafe_allow_html=True,
                )

question = st.chat_input(
    "Ask about products, shipping, returns...",
    key="support_question",
)
if question:
    process_question(question)
