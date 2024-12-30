# streamlit_app.py
import streamlit as st
import asyncio
import os
from src.llm.deepseek.inference import run_deepseek_stream
from src.llm.gpt.inference import run_gpt_stream

try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# Streamlit 설정
st.set_page_config(page_title="Posplexity", layout="wide")
st.title("POSTECH 25학번 입학을 환영합니다!")

# 모델 선택 라디오 버튼 추가
model_choice = st.sidebar.radio(
    "모델 선택",
    ["GPT", "DeepSeek"],
    captions=["OpenAI GPT 모델", "DeepSeek 모델"]
)

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
        message_placeholder = st.empty()

        async def get_response():
            try:
                if model_choice == "GPT":
                    stream = await run_gpt_stream(
                        target_prompt=prompt,
                        prompt_in_path="chat_basic.json"
                    )
                else:  # DeepSeek
                    stream = await run_deepseek_stream(
                        target_prompt=prompt,
                        prompt_in_path="chat_basic.json"
                    )
                
                full_response = ""
                async for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        full_response += chunk.choices[0].delta.content
                        message_placeholder.markdown(full_response)
                return full_response
            except Exception as e:
                raise Exception(f"응답 생성 중 오류 발생: {str(e)}")

        try:
            with st.spinner("응답 생성 중..."):
                response = loop.run_until_complete(get_response())
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response
                })
        except Exception as e:
            message_placeholder.error(f"오류가 발생했습니다: {str(e)}")