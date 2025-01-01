import sys, os, asyncio, json
sys.path.append(os.path.abspath("")) 

from dotenv import load_dotenv
from src.utils import upload_s3  # 이미 작성된 업로드 함수
from common.config import POSTECH_BUCKET_NAME, POSTECH_REGION_NAME  

import streamlit as st
import boto3
from botocore.exceptions import ClientError

load_dotenv()


def make_page():
    st.set_page_config(page_title="Posplexity upload", layout="centered")

    st.image(
        "data/assets/postech/posplexity_for_postech.png",
        use_column_width=True
    )
    st.title("데이터 업로드")
    st.caption("powered by posplexity")

    # S3 접근 정보
    access_key = os.getenv("S3_ACCESS_KEY")
    secret_key = os.getenv("S3_SECRET_ACCESS_KEY")

    # 다중 파일 업로더 (key 설정하여 상태 관리)
    uploaded_files = st.file_uploader(
        label="",
        type=["pdf", "docx"],
        accept_multiple_files=True,
        key="file_uploader"
    )

    # 업로드 버튼
    if st.button("Upload"):
        # 파일이 선택되지 않았다면 경고
        if not uploaded_files:
            st.warning("업로드할 파일을 선택해 주세요.")
            return

        # 여기서 로딩 동그라미(Spinner) 표시
        with st.spinner("업로드 중입니다... 잠시만 기다려 주세요."):
            upload_s3(
                files=uploaded_files,
                access_key=access_key,
                secret_key=secret_key,
                region_name=POSTECH_REGION_NAME,
                bucket_name=POSTECH_BUCKET_NAME+"/staged"
            )
        st.success("파일 업로드가 완료되었습니다!")
        
        # 업로드 후 페이지 재실행
        st.rerun()

# 실행 스크립트
if __name__ == "__main__":
    make_page()