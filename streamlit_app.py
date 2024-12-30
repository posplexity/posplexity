# streamlit_app.py
import streamlit as st
import asyncio
import os
from src.deepseek.inference import run_deepseek_stream
from src.gpt.inference import run_gpt_stream

try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# Streamlit 설정
st.set_page_config(page_title="DeepSeek 챗봇", layout="wide")
st.title("DeepSeek 챗봇")

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
            stream = await run_gpt_stream(
                target_prompt=prompt,
                prompt_in_path="chat_basic.json"
            )
            full_response = ""
            async for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    full_response += chunk.choices[0].delta.content
                    message_placeholder.markdown(full_response)
            
            # 응답이 완료된 후 2초 대기
            return full_response

        try:
            with st.spinner("응답 생성 중..."):
                response = loop.run_until_complete(get_response())
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response
                })
        except Exception as e:
            message_placeholder.error(f"오류가 발생했습니다: {str(e)}")