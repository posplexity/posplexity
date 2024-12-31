from src.llm.deepseek.inference import run_deepseek_stream, run_deepseek
from src.llm.gpt.inference import run_gpt
from src.search.search import search 
from src.utils.utils import async_wrapper
import streamlit as st
import streamlit.components.v1 as components
import asyncio, json
from common.types import intlist_struct
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

name_source_mapping = json.load(open("data/mapping.json", "r"))

def setup_sidebar():
    """
    사이드바 UI를 구성하고, 전역 변수에 모델 선택/옵션을 세팅한다.
    """
    try:
        st.sidebar.image(
            "data/assets/postech_logo.svg",
            use_container_width=True
        )
    except:
        st.sidebar.image(
            "data/assets/postech_logo.svg",
            use_column_width=True
        )

    st.sidebar.markdown("""
    \n새내기 여러분의 궁금증을 해소하기 위해 관련 자료를 기반으로 답변을 제공하는 챗봇입니다.
    """)

    # 예시 질문 섹션
    with st.sidebar.expander("ℹ️ 예시 질문", expanded=True):
        example_questions = [
            "밥약이 무슨 뜻인가요?",
            "새터 기간동안 술을 마셔도 괜찮나요?",
            "야구를 좋아하는데, 어떤 동아리에 들어가는게 좋을까요?",
        ]
        for question in example_questions:
            if st.button(question):
                st.session_state.pending_question = question
                st.rerun()

    st.sidebar.divider()

    with st.sidebar.expander("💬 문의하기", expanded=False):
        st.markdown("""                    
            ### Contact
            궁금한 점이나 피드백은 언제든지 아래 페이지를 통해 공유해 주세요.
            - [문의사항 페이지](https://forms.gle/aMAJA7yPFfCRGLro9)
                    
            ### Contributing
            자료를 보완하거나 새롭게 추가하고 싶은 내용이 있다면, 아래 업로드 페이지를 이용해 주시기 바랍니다.
            - [업로드 페이지](https://docs.google.com/forms/d/e/1FAIpQLScUW14gj69mWXlhoKpJejBLWCbj-wOQZ4e6XQT69ZFNWZS4SA/viewform)
        """)

    with st.sidebar.expander("👨‍👩‍👦‍👦 제작자", expanded=False):
        st.markdown("""
            ### Contributers
            [**허채원**](https://www.linkedin.com/in/cwhuh/)(포스텍 24),  
            [**최지안**](https://www.linkedin.com/in/%EC%A7%80%EC%95%88-%EC%B5%9C-72093030a/)(포스텍 24),  
            [**최주연**](https://www.linkedin.com/in/%EC%A3%BC%EC%97%B0-%EC%B5%9C-a9884331b/)(포스텍 24),  
            [**정찬희**](https://www.linkedin.com/in/%EC%B0%AC%ED%9D%AC-%EC%A0%95-b6506b328/)(포스텍 24)
        """)

    with st.sidebar.expander("💻 코드", expanded=False):
        st.markdown("""
            전체 코드는 오픈소스로 공개되어 있습니다.  
            [**GitHub**](https://github.com/chaewon-huh/posplexity)
        """)


def setup_page():
    """
    메인 페이지(본문) 설정을 담당. 타이틀, 부가 문구 등을 표시.
    """
    st.title("POSTECH 25학번 입학을 환영합니다!")
    st.caption("powered by P13")


# Streamlit Settings
st.set_page_config(page_title="Posplexity", layout="wide")

# 사이드바와 페이지 구성
setup_sidebar()
setup_page()

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []  # [{role: "user"/"assistant", content: "..."}]


# 기존 채팅 기록 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# 예시 질문 처리 - pending_question
prompt = None

# (a) 먼저, 예시 질문 버튼 클릭으로 저장된 pending_question이 있으면 사용
if "pending_question" in st.session_state:
    prompt = st.session_state.pending_question
    del st.session_state.pending_question  # 한 번 사용 후 삭제

# (b) 사용자가 직접 입력한 채팅이 있으면 그걸로 대체
user_input = st.chat_input("질문을 입력하세요")
if user_input:
    prompt = user_input

if prompt:
    # 1. 사용자 메시지 표시
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. 챗봇 응답 (LLM 호출)
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        reference_placeholder = st.empty()  # 출처 표시용

        async def get_response():
            """
            사용자 질의를 받아서,
            1. RAG 검색 (top_k=20)
            2. LLM Re-ranking -> 상위 ID 추출
            3. 최종 RAG 컨텍스트를 생성해 답변 (스트리밍)
            """
            try:
                # (1) 대화 히스토리 정리
                history_text = ""
                for msg in st.session_state.messages[:-1]:
                    if msg["role"] == "user":
                        history_text += f"User: {msg['content']}\n"
                    elif msg["role"] == "assistant":
                        history_text += f"Assistant: {msg['content']}\n"

                # (2) RAG 검색
                found_chunks = []
                with st.spinner("문서를 조회 중입니다..."):
                    found_chunks = search(prompt, top_k=20, dev=False)

                # (3) Re-ranking
                # 각 청크: c["id"], c["doc_title"], c["raw_text"], c["doc_source"], c["page_num"] ...
                # 3-1. (id, text_summary) 형태의 딕셔너리 구성
                chunk_dict = {
                    c["id"]: (c["doc_title"], c["summary"])
                    for c in found_chunks
                }

                # 3-2. Re-ranking을 위해 LLM 호출 (스피너 추가)
                with st.spinner("문서를 재정렬 중입니다..."):
                    reranked_chunks = run_gpt(
                        target_prompt=str(chunk_dict),       # LLM에 넘길 문자열 (id -> title & 요약)
                        prompt_in_path="reranking.json",     # reranking를 수행하는 JSON prompt
                        gpt_model="gpt-4o-2024-08-06",
                        output_structure=intlist_struct
                    )

                reranked_ids = reranked_chunks.output

                # (4) re-ranked된 id에 해당하는 청크만 추출
                filtered_chunks = [c for c in found_chunks if c["id"] in reranked_ids]

                # (4-1) re-ranked 리스트 순서 유지 위해 id -> index 매핑
                id_to_rank = {id_: idx for idx, id_ in enumerate(reranked_ids)}
                sorted_chunks = sorted(filtered_chunks, key=lambda x: id_to_rank[x["id"]])

                # (4-2) 최종 RAG 컨텍스트 구성
                context_texts = [c["raw_text"] for c in sorted_chunks]
                rag_context = "\n".join(context_texts)
                final_prompt = f"""
아래는 이전 대화의 기록입니다:
{history_text}

다음은 참고 자료(RAG)에서 발췌한 내용입니다:
{rag_context}

이제 사용자의 질문을 다시 안내해 드리겠습니다:

질문: {prompt}

위 대화와 자료를 기반으로 답변을 작성해 주세요.
답변:
"""

                # (5) 최종 답변 (스트리밍)
                stream = await run_deepseek_stream(
                    target_prompt=final_prompt,
                    prompt_in_path="chat_basic.json"
                )

                full_response = ""
                async for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        full_response += chunk.choices[0].delta.content
                        message_placeholder.markdown(full_response)

                # (6) 출처 표시 - 최종 사용된 sorted_chunks 기준
                if sorted_chunks:
                    dedup_set = set()
                    for c in sorted_chunks:
                        doc_title = c.get("doc_title", "Untitled")
                        doc_source = c.get("doc_source", "Unknown Source")
                        # name_source_mapping에서 매핑
                        if not doc_source.startswith("http"):
                            doc_source = name_source_mapping.get(doc_title, doc_source)
                        page_num = c.get("page_num", None)
                        dedup_set.add((doc_title, doc_source, page_num))

                    refs = []
                    for idx, (title, source, page) in enumerate(dedup_set, start=1):
                        if source.startswith("http"):
                            if page is not None:
                                refs.append(f"- **{title}** (p.{page}) / [링크로 이동]({source})")
                            else:
                                refs.append(f"- **{title}** / [링크로 이동]({source})")
                        else:
                            if page is not None:
                                refs.append(f"- **{title}** (p.{page}) / {source}")
                            else:
                                refs.append(f"- **{title}** / {source}")

                    refs_text = "\n".join(refs)
                    reference_placeholder.markdown(
                        f"---\n**참고 자료 출처**\n\n{refs_text}\n"
                    )

                return full_response

            except Exception as e:
                raise Exception(f"응답 생성 중 오류가 발생했습니다: {str(e)}")

        try:
            # 비동기 응답 처리
            response = loop.run_until_complete(get_response())
            st.session_state.messages.append({
                "role": "assistant",
                "content": response
            })
        except Exception as e:
            message_placeholder.error(f"오류가 발생했습니다: {str(e)}")