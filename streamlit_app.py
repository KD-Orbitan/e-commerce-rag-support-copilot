import os
import streamlit as st
from dotenv import load_dotenv


load_dotenv()


def configure_secrets() -> None:
    """Map Streamlit secrets to the environment variables used by the existing app."""
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

# Import after secrets are mapped so app.config uses the selected models.
from app.rag.ingest import ensure_index
from app.rag.pipeline import run_rag


@st.cache_resource(show_spinner=False)
def initialize_index() -> str:
    return ensure_index()


st.set_page_config(
    page_title="Orbit Shop Support Copilot",
    page_icon="shop",
    layout="centered",
)

st.title("Orbit Shop - AI Support Copilot")
st.caption("Tra loi duoc ho tro boi tai lieu cua cua hang.")

if "messages" not in st.session_state:
    st.session_state.messages = []

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.warning(
        "Demo chua duoc cau hinh OPENAI_API_KEY. "
        "Vui long them key trong Streamlit Secrets."
    )
else:
    try:
        index_status = initialize_index()
        st.caption(index_status)
    except Exception as exc:
        st.error(
            "Khong the khoi tao co so du lieu. "
            f"{type(exc).__name__}."
        )


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant" and message.get("sources"):
            with st.expander("Nguon tai lieu da truy xuat"):
                for source in message["sources"]:
                    st.markdown(
                        f"- **{source['source']}** "
                        f"(chunk: `{source['id']}`, "
                        f"distance: `{source['distance']:.4f}`)"
                    )


question = st.chat_input("Nhap cau hoi cua ban...")

if st.button("Xoa cuoc tro chuyen"):
    st.session_state.messages = []
    st.rerun()

if question:
    question = question.strip()
    if question:
        st.session_state.messages.append({
            "role": "user",
            "content": question,
        })

        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Dang truy xuat tai lieu va tao cau tra loi..."):
                try:
                    result = run_rag(question=question, top_k=3)
                    answer = result["answer"]
                    sources = result.get("sources", [])
                except Exception:
                    answer = (
                        "Xin loi, dich vu AI dang gap su co. "
                        "Vui long thu lai sau."
                    )
                    sources = []

            st.markdown(answer)
            if sources:
                with st.expander("Nguon tai lieu da truy xuat"):
                    for source in sources:
                        st.markdown(
                            f"- **{source['source']}** "
                            f"(chunk: `{source['id']}`, "
                            f"distance: `{source['distance']:.4f}`)"
                        )

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "sources": sources,
        })
