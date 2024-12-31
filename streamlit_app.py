# streamlit_app.py
import streamlit as st
import asyncio
import os
import streamlit.components.v1 as components  # iFrame 임베드용

from src.llm.deepseek.inference import run_deepseek_stream
from src.llm.gpt.inference import run_gpt_stream
from src.search.search import search  # Qdrant 벡터 검색 함수

try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# 전역 변수처럼 쓸 수 있도록 이곳에서 선언 (혹은 setup_sidebar에서 반환받아도 됨)
model_choice = None
use_rag = True

def setup_sidebar():
    """
    사이드바 UI를 구성하고, 전역 변수에 모델 선택/옵션을 세팅한다.
    """
    global model_choice, use_rag

    ########################################
    # (1) 사이드바 최상단 로고 표시
    ########################################
    st.sidebar.image(
        "assets/postech_logo.svg",
        use_column_width=True
    )
    # --------------------------------------

    st.sidebar.markdown("""
    \n새내기들의 불편함을 최소화하기 위해, 근거자료를 기반으로 답변하는 챗봇을 제작하였습니다.
    """)

    # 예시 질문 섹션
    with st.sidebar.expander("ℹ️ 예시 질문", expanded=True):
        example_questions = [
            "밥약이 무슨 뜻인가요?",
            "1학년 기숙사에서 술을 마실 수 있나요?",
            "포스텍 밴드 동아리에는 어떤게 있나요?",
        ]
        for question in example_questions:
            if st.button(question):
                # 질문을 세션에 저장, rerun 후 main에서 처리
                st.session_state.pending_question = question
                st.rerun()

    st.sidebar.divider()

    # 문의하기
    with st.sidebar.expander("💬 문의하기", expanded=False):
        st.markdown("""
            ### Contact
            응답 문서 및 자료 제보, 추가 기능 제안, 피드백 사안은 모두 하기 이메일로 정리하여 보내주시면 감사하겠습니다.
            - cw.huh@postech.ac.kr
        """)

    # 제작자
    with st.sidebar.expander("👨‍👩‍👦‍👦 제작자", expanded=False):
        st.markdown("""
            ### Contributers
            [**허채원**](https://www.linkedin.com/in/cwhuh/)(포스텍 24),  
            [**최지안**](https://www.linkedin.com/in/%EC%A7%80%EC%95%88-%EC%B5%9C-72093030a/)(포스텍 24),  
            [**최주연**](https://www.linkedin.com/in/%EC%A3%BC%EC%97%B0-%EC%B5%9C-a9884331b/)(포스텍 24),  
            [**정찬희**](https://www.linkedin.com/in/%EC%B0%AC%ED%9D%AC-%EC%A0%95-b6506b328/)(포스텍 24)
        """)

    # 코드
    with st.sidebar.expander("💻 코드", expanded=False):
        st.markdown("""
            전체 코드는 공개되어 있으며, 자유로운 활용이 가능합니다.  
            [**GitHub**](https://github.com/chaewon-huh/posplexity)
        """)

    # (필요하면 모델 선택, RAG 옵션 복구)
    # model_choice = st.sidebar.radio(
    #     "모델 선택",
    #     ["DeepSeek", "GPT"],
    #     captions=["DeepSeek-v3", "gpt-4o-mini (비추천)"]
    # )
    # use_rag = st.sidebar.checkbox("Use RAG", value=True, help="벡터 검색 기반으로 문서를 참고")


def setup_page():
    """
    메인 페이지(본문) 설정을 담당. 타이틀, 부가 문구 등을 표시.
    """
    st.title("POSTECH 25학번 입학을 환영합니다!")
    st.caption("powered by P13")


#############################################
# Streamlit 기본 설정
#############################################
st.set_page_config(page_title="Posplexity", layout="wide")

# 먼저 사이드바와 페이지 구성
setup_sidebar()
setup_page()

#############################################
# (1) 세션 상태 초기화
#############################################
if "messages" not in st.session_state:
    st.session_state.messages = []  # [{role: "user"/"assistant", content: "..."}]

#############################################
# (2) 기존 채팅 기록 표시
#############################################
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

#############################################
# (3) 예시 질문 처리 - pending_question
#############################################
prompt = None

# (a) 먼저, 예시 질문 버튼 클릭으로 저장된 pending_question이 있으면 사용
if "pending_question" in st.session_state:
    prompt = st.session_state.pending_question
    del st.session_state.pending_question  # 한 번 사용 후 삭제

# (b) 사용자가 직접 입력한 채팅이 있으면 그걸로 대체
user_input = st.chat_input("메시지를 입력하세요")
if user_input:
    prompt = user_input

#############################################
# (4) prompt가 최종 결정되면 -> 모델 호출
#############################################
if prompt:
    # 1) 사용자 메시지 표시
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2) 챗봇 응답 (LLM 호출)
    with st.chat_message("assistant"):
        # 메시지 출력 영역 2개: (1) 모델 답변용, (2) 출처 표시용
        message_placeholder = st.empty()
        reference_placeholder = st.empty()  # 출처 표시용

        async def get_response():
            """
            사용자 질의를 받아서,
            1) (옵션) RAG 검색
            2) 이전 대화 히스토리 + (옵션) RAG 컨텍스트 -> LLM에 전달 (스트리밍)
            3) 스트리밍 결과 반환
            """
            try:
                # (a) 이전 대화 히스토리를 하나의 문자열로 합치기
                history_text = ""
                # 마지막(현재 발화한 user 메시지)은 제외하고 합침
                for msg in st.session_state.messages[:-1]:
                    if msg["role"] == "user":
                        history_text += f"User: {msg['content']}\n"
                    elif msg["role"] == "assistant":
                        history_text += f"Assistant: {msg['content']}\n"
                
                # (b) RAG 검색(옵션) -- use_rag, model_choice가 주석 처리되어있으니
                #    기본값(True)로 두거나 필요에 맞게 수정
                found_chunks = []
                if use_rag:
                    with st.spinner("문서 탐색 중..."):
                        found_chunks = search(prompt, top_k=5)  # Qdrant 벡터 검색
                
                # 검색된 청크들을 합쳐서 RAG 컨텍스트 생성
                context_texts = [c["raw_text"] for c in found_chunks]
                rag_context = "\n".join(context_texts)

                # (c) 최종 Prompt 생성
                final_prompt = f"""
아래는 이전에 진행된 대화입니다:
{history_text}

그리고 아래는 RAG 검색에서 찾은 참고 자료입니다:
{rag_context}

이제 사용자 질문을 다시 안내해 드리겠습니다:

질문: {prompt}

위 대화와 자료를 참고하여 답변을 생성해 주세요.
답변:
"""

                # (d) LLM에 프롬프트 전달 (스트리밍)
                # model_choice가 None일 가능성이 있으니, 기본값 처리
                selected_model = model_choice if model_choice else "DeepSeek"

                if selected_model == "GPT":
                    stream = await run_gpt_stream(
                        target_prompt=final_prompt,
                        prompt_in_path="chat_basic.json"
                    )
                else:  # "DeepSeek"
                    stream = await run_deepseek_stream(
                        target_prompt=final_prompt,
                        prompt_in_path="chat_basic.json"
                    )
                
                # (e) 스트리밍 결과 처리 (메시지 누적하여 표시)
                full_response = ""
                async for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        full_response += chunk.choices[0].delta.content
                        message_placeholder.markdown(full_response)

                # (f) 검색된 청크의 출처 만들기 (옵션)
                if use_rag and found_chunks:
                    dedup_set = set()
                    for c in found_chunks:
                        doc_source = c.get("doc_source", "Unknown Source")
                        doc_title = c.get("doc_title", "Untitled")
                        page_num = c.get("page_num", None)  # PDF 페이지 번호
                        dedup_set.add((doc_title, doc_source, page_num))

                    refs = []
                    for idx, (title, source, page) in enumerate(dedup_set, start=1):
                        if page is not None:
                            refs.append(f"- **{title}** (p.{page}) / {source}")
                        else:
                            refs.append(f"- **{title}** / {source}")
                    
                    refs_text = "\n".join(refs)
                    reference_placeholder.markdown(
                        f"---\n**참고 문서(청크) 출처**\n\n{refs_text}\n"
                    )

                return full_response

            except Exception as e:
                raise Exception(f"응답 생성 중 오류 발생: {str(e)}")

        try:
            # 비동기 응답 처리
            response = loop.run_until_complete(get_response())
            st.session_state.messages.append({
                "role": "assistant",
                "content": response
            })
        except Exception as e:
            message_placeholder.error(f"오류가 발생했습니다: {str(e)}")