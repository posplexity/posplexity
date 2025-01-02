import sys, os, asyncio, json
sys.path.append(os.path.abspath("")) 

import streamlit as st
from core import get_response

try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

name_source_mapping = json.load(open("data/mapping.json", "r"))

def _get_selected_filters():
    """체크된 항목만 필터 리스트로 만들어 반환. 없으면 None."""
    filter_keys = ["official", "email", "everytime"]
    selected = [f for f in filter_keys if st.session_state.get(f)]
    return selected if selected else None

def setup_sidebar():
    """사이드바 UI 구성"""

    # posplexity 로고
    st.sidebar.image(
        "data/assets/postech/posplexity_for_postech.png",
        use_container_width=True
    )
    
    st.sidebar.markdown("""
    \n새내기 여러분의 궁금증을 해소하기 위해 관련 자료를 기반으로 답변을 제공하는 챗봇입니다.
    """)

    # 예시 질문 
    with st.sidebar.expander("ℹ️ 예시 질문", expanded=True):
        example_questions = [
            "교내에 셔틀버스가 다니나요?",
            "기숙사(생활관) 비용은 어느정도인가요?",
            "교내 자전거 대여 서비스가 존재하나요?",
        ]
        for question in example_questions:
            if st.button(question):
                st.session_state.pending_question = question
                st.rerun()

    with st.sidebar.expander("⚙️ 설정", expanded=False):
        st.markdown("### 검색 소스")
        st.caption("**1/4까지 개발 예정입니다.**")
        st.caption("에브리타임 검색 시, 정확하지 않은 정보가 탐색될 수 있습니다.")
        st.checkbox("공식 문서", value=True, key="official", disabled=True)
        st.checkbox("교내회보메일", value=True, key="email", disabled=True) 
        st.checkbox("에브리타임", value=True, key="everytime", disabled=True)
        

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
            ### Contributors
            [**허채원**](https://www.linkedin.com/in/cwhuh/)(포스텍 24),  
            [**최지안**](https://www.linkedin.com/in/%EC%A7%80%EC%95%88-%EC%B5%9C-72093030a/)(포스텍 24),  
            [**최주연**](https://www.linkedin.com/in/%EC%A3%BC%EC%97%B0-%EC%B5%9C-a9884331b/)(포스텍 24),  
            [**정찬희**](https://www.linkedin.com/in/%EC%B0%AC%ED%9D%AC-%EC%A0%95-b6506b328/)(포스텍 24)
        """)

    with st.sidebar.expander("📃 릴리즈 노트", expanded=False):
        st.markdown("""
            ### 2025.01.02
            - 릴리즈 노트 추가
            - 2024 교내 회보 메일 DB 추가
            - 모델 변경 (Gemini 2.0 Flash Exp)
            - UI 개선
                    
            ### 2024.12.31
            - 초기 릴리즈
                    
            [Full notes](https://chaewonhuh.notion.site/Release-notes-16f60dcdee58809ea7f9de60e31d0995?pvs=4)
        """)


def setup_page():
    """메인 페이지(본문) 설정을 담당. 타이틀, 부가 문구 등을 표시."""

    st.title("포스텍 2025 입학을 축하합니다!")
    st.caption("powered by posplexity")


# Streamlit Settings
st.set_page_config(page_title="Posplexity", layout="wide")

setup_sidebar()
setup_page()

hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True) 

# Default messages
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "안녕하세요! 저는 POSTECH 새내기 여러분을 도와드리는 포닉스입니다.\n"
                "무엇이든 궁금한 점이 있다면 편하게 물어보세요."
            )
        }
    ]


USER_AVATAR = "data/assets/postech/baby_ponix.png"
ASSISTANT_AVATAR = "data/assets/postech/ponix_official.png"

# 과거 대화 출력
for message in st.session_state.messages:
    role = message["role"]
    content = message["content"]

    if role == "assistant":
        with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
            st.markdown(content)
    else:
        # 이 예시에서는 user 외에 system 같은 role도 동일하게 user 아바타로 처리
        with st.chat_message("user", avatar=USER_AVATAR):
            st.markdown(content)

# 예시 질문 처리 / user_input
prompt = None
if "pending_question" in st.session_state:
    prompt = st.session_state.pending_question
    del st.session_state.pending_question

user_input = st.chat_input("질문을 입력하세요")
if user_input:
    prompt = user_input

if prompt:
    # 사용자 메시지 표시
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 코어 로직 호출
    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):

        try:
            selected_filters = _get_selected_filters()

            # TODO : 데이터 재업로드 이후 제거 (현재는 Filter가 전체에 걸려있지 않아, everytime만 정제)
            if "everytime" not in selected_filters:
                selected_filters = ["everytime"]

            final_response = get_response(
                prompt=prompt,
                messages=st.session_state.messages,
                name_source_mapping=name_source_mapping,
                filter=selected_filters
            )
            # 최종 응답을 세션 메시지에 저장
            st.session_state.messages.append({
                "role": "assistant",
                "content": final_response
            })

            # 방금 생성된 assistant 메시지의 본문도 표시
            # st.markdown(final_response)

        except Exception as e:
            st.error(f"오류가 발생했습니다: {str(e)}")