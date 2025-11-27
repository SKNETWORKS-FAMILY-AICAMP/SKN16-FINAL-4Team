import logging
from typing import List
import sys
from pathlib import Path

# Ensure project root is on sys.path so `rag_service` package is importable
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import streamlit as st

from rag_service.api.app import rag_system


class ListHandler(logging.Handler):
    """Logging handler that stores formatted records in a list."""

    def __init__(self, buffer: List[str]):
        super().__init__()
        self.buffer = buffer

    def emit(self, record):
        try:
            msg = self.format(record)
        except Exception:
            msg = record.getMessage()
        self.buffer.append(msg)


def main():
    st.set_page_config(page_title="RAG Service Streamlit Chat", layout="wide")
    st.title("🤖 RAG Service — Streamlit Test Chat")

    st.markdown("""
    간단한 질의 입력으로 라우팅과 RAG 처리(불변/가변)를 테스트합니다.
    - **불변 지식**: 퍼스널 컬러 (Gemini)
    - **가변 지식**: Vogue 트렌드 (OpenAI)
    """)

    # Initialize session state for chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    if "logs_history" not in st.session_state:
        st.session_state.logs_history = []

    # Sidebar controls
    with st.sidebar:
        st.header("⚙️ 설정")
        
        temp = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1)
        max_tokens = st.number_input("Max Tokens", 64, 4096, 1024, 64)
        force_route = st.selectbox("강제 라우팅 (선택)", 
                                   options=[None, 1, 2, 3, 4], 
                                   format_func=lambda x: "자동" if x is None else f"Route {x}",
                                   index=0)
        
        st.divider()
        
        st.subheader("📊 현재 상태")
        st.metric("불변 파일", len(rag_system.immutable_handler.uploaded_files))
        st.metric("가변 파일", len(rag_system.mutable_handler.uploaded_files))
        
        st.divider()
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 가변 재동기화", use_container_width=True):
                try:
                    rag_system.mutable_handler._load_files()
                    st.success("✅ 재동기화 완료")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 실패: {e}")
        
        with col2:
            if st.button("🗑️  채팅 초기화", use_container_width=True):
                st.session_state.chat_history = []
                st.session_state.logs_history = []
                st.rerun()

    # Main chat area
    st.subheader("💬 채팅")
    
    # Display chat history
    chat_container = st.container()
    with chat_container:
        for i, msg in enumerate(st.session_state.chat_history):
            with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "🤖"):
                st.markdown(msg["content"])
                
                # Show detailed response for assistant messages
                if msg["role"] == "assistant" and "metadata" in msg:
                    with st.expander("📋 상세 정보"):
                        st.json(msg["metadata"])

    # Input area
    st.divider()
    
    col1, col2 = st.columns([4, 1])
    with col1:
        user_input = st.text_input(
            "질문 입력...",
            placeholder="예: 봄 웜톤의 특징은?",
            key="user_input_field"
        )
    
    with col2:
        send_button = st.button("📤 전송", use_container_width=True)

    # Process query
    if send_button and user_input and user_input.strip():
        # Add user message
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_input
        })

        # Run query with logging
        with st.spinner("⏳ 처리 중..."):
            logs, result = run_query(
                question=user_input,
                temperature=temp,
                max_tokens=max_tokens,
                force_route=force_route
            )

        # Add assistant response
        if result and result.get("success"):
            assistant_msg = {
                "role": "assistant",
                "content": result.get("answer", "답변을 생성하지 못했습니다."),
                "metadata": {
                    "success": result.get("success"),
                    "source": result.get("metadata", {}).get("source", "unknown"),
                    "route": result.get("metadata", {}).get("route"),
                }
            }
        else:
            error_msg = result.get("error", "알 수 없는 오류") if result else "쿼리 처리 실패"
            assistant_msg = {
                "role": "assistant",
                "content": f"❌ 오류: {error_msg}",
                "metadata": {"success": False}
            }

        st.session_state.chat_history.append(assistant_msg)
        st.session_state.logs_history.append({
            "question": user_input,
            "logs": logs
        })

        # Rerun to display new messages
        st.rerun()

    # Display logs expander (if any)
    if st.session_state.logs_history:
        with st.expander("📝 실행 로그", expanded=False):
            for i, log_entry in enumerate(st.session_state.logs_history[-1:]):
                st.write(f"**질문**: {log_entry['question']}")
                st.code('\n'.join(log_entry['logs']), language='log')


def run_query(question: str, temperature: float, max_tokens: int, force_route) -> tuple:
    """
    Run RAG query and capture logs.
    
    Returns:
        (logs: List[str], result: Dict)
    """
    logs: List[str] = []
    handler = ListHandler(logs)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    original_level = root_logger.level
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)

    rs_logger = logging.getLogger("rag_service")
    rs_logger.setLevel(logging.INFO)
    rs_logger.addHandler(handler)

    try:
        # Run query
        result = rag_system.query(
            question=question,
            temperature=temperature,
            max_tokens=max_tokens,
            force_route=force_route
        )
        
        # Ensure result has proper structure
        if not isinstance(result, dict):
            result = {
                "success": False,
                "error": f"Unexpected response type: {type(result)}",
                "answer": str(result)
            }
        
        if "success" not in result:
            result["success"] = bool(result.get("answer"))
        
        return logs, result

    except Exception as e:
        logger_instance = logging.getLogger(__name__)
        logger_instance.error(f"❌ 쿼리 실패: {e}", exc_info=True)
        return logs, {
            "success": False,
            "error": str(e),
            "answer": f"오류 발생: {str(e)}"
        }

    finally:
        root_logger.removeHandler(handler)
        rs_logger.removeHandler(handler)
        root_logger.setLevel(original_level)


if __name__ == "__main__":
    main()
