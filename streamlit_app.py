# streamlit_app.py
import streamlit as st
import asyncio
import os

from src.llm.deepseek.inference import run_deepseek_stream
from src.llm.gpt.inference import run_gpt_stream

# 추가: RAG 검색
from src.search.search import search  # Qdrant 벡터 검색 함수

try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# Streamlit 설정
st.set_page_config(page_title="Posplexity", layout="wide")
st.title("POSTECH 25학번 입학을 환영합니다!")

# 모델 선택 라디오 버튼
model_choice = st.sidebar.radio(
    "모델 선택",
    ["GPT", "DeepSeek"],
    captions=["OpenAI GPT 모델", "DeepSeek 모델"]
)

# RAG 옵션 추가 (예: 체크박스)
use_rag = st.sidebar.checkbox("Use RAG", value=True, help="벡터 검색 기반으로 문서를 참고")

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 채팅 기록 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 채팅 입력
if prompt := st.chat_input("메시지를 입력하세요"):
    # 사용자 메시지 표시
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 챗봇 응답
    with st.chat_message("assistant"):
        # 메시지 출력 영역 2개: (1) 모델 답변용, (2) 출처 표시용
        message_placeholder = st.empty()
        reference_placeholder = st.empty()  # 출처 표시용

        async def get_response():
            """
            사용자 질의를 받아서,
            1) (옵션) RAG 검색
            2) LLM에 프롬프트 전달 (스트리밍)
            3) 스트리밍 결과 반환
            """
            try:
                final_prompt = prompt
                found_chunks = []

                if use_rag:
                    # (옵션) 문서 탐색 중... 표시
                    with st.spinner("문서 탐색 중..."):
                        # 1) RAG 검색
                        found_chunks = search(prompt, top_k=3)
                    
                    # 검색된 청크들을 프롬프트에 추가
                    context_texts = [c["raw_text"] for c in found_chunks]
                    context = "\n".join(context_texts)

                    # RAG용 프롬프트 생성 (간단 예시)
                    final_prompt = f"""아래 정보를 참고하여 질문에 답해줘:
{context}

질문: {prompt}
답변:
"""

                # 2) 최종 프롬프트를 LLM에 전달
                # (스피너 없이 실행)
                if model_choice == "GPT":
                    stream = await run_gpt_stream(
                        target_prompt=final_prompt,
                        prompt_in_path="chat_basic.json"
                    )
                else:  # DeepSeek
                    stream = await run_deepseek_stream(
                        target_prompt=final_prompt,
                        prompt_in_path="chat_basic.json"
                    )
                
                # 3) 스트리밍 결과 처리 (모델 답변)
                full_response = ""
                async for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        full_response += chunk.choices[0].delta.content
                        message_placeholder.markdown(full_response)

                # (추가) 검색된 청크의 출처 만들기
                if use_rag and found_chunks:
                    # 중복 제거 위해 set 사용
                    # page_num 등도 함께 표시
                    # (doc_title, doc_source, page_num) 형태로 저장
                    dedup_set = set()
                    for c in found_chunks:
                        doc_source = c.get("doc_source", "Unknown Source")
                        doc_title = c.get("doc_title", "Untitled")
                        page_num = c.get("page_num", None)  # PDF 페이지 번호
                        # 튜플로 묶어서 set에 추가
                        dedup_set.add((doc_title, doc_source, page_num))

                    # set -> 리스트 변환 후 출력
                    refs = []
                    for idx, (title, source, page) in enumerate(dedup_set, start=1):
                        if page is not None:
                            # PDF page_num 있는 경우
                            refs.append(f"- **{title}** (p.{page}) / {source}")
                        else:
                            # Word나 page_num이 없는 경우
                            refs.append(f"- **{title}** / {source}")
                    
                    # 출처 목록 작성
                    refs_text = "\n".join(refs)
                    reference_placeholder.markdown(
                        f"---\n**참고 문서(청크) 출처**\n\n{refs_text}\n"
                    )

                return full_response

            except Exception as e:
                raise Exception(f"응답 생성 중 오류 발생: {str(e)}")

        try:
            # 모델 답변 생성 (스피너 없음)
            response = loop.run_until_complete(get_response())
            st.session_state.messages.append({
                "role": "assistant",
                "content": response
            })
        except Exception as e:
            message_placeholder.error(f"오류가 발생했습니다: {str(e)}")