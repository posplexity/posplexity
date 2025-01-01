# FOR ADMIN
import sys, os
sys.path.append(os.path.abspath("")) 

from dotenv import load_dotenv
from src.utils.utils import upload_s3, list_s3_objects, generate_presigned_url
from common.config import POSTECH_BUCKET_NAME, POSTECH_REGION_NAME  
from update import upload

import streamlit as st
import pandas as pd

load_dotenv()

def make_page():
    st.set_page_config(page_title="Posplexity upload", layout="centered")

    st.image(
        "data/assets/postech/posplexity_for_postech.png",
        use_container_width=True
    )
    st.title("데이터 업로드 for admin")
    st.caption("powered by posplexity")

    # S3 접근 정보
    access_key = os.getenv("S3_ACCESS_KEY")
    secret_key = os.getenv("S3_SECRET_ACCESS_KEY")

    # 이미 업로드된 파일 목록 가져오기 (prefix="uploaded/")
    existing_files = list_s3_objects(
        bucket_name=POSTECH_BUCKET_NAME,
        region_name=POSTECH_REGION_NAME,
        access_key=access_key,
        secret_key=secret_key,
        prefix="uploaded/"  
    )

    st.subheader("이미 업로드된 파일 목록")

    if existing_files:
        # 1) DataFrame 생성
        df = pd.DataFrame({"S3 Key": existing_files})

        # 2) "Download" 열 추가 - 아이콘 or 텍스트 링크
        download_links = []
        for key in existing_files:
            url = generate_presigned_url(
                bucket_name=POSTECH_BUCKET_NAME,
                region_name=POSTECH_REGION_NAME,
                access_key=access_key,
                secret_key=secret_key,
                file_key=key,
            )
            if url:
                # 다운로드 아이콘 (이모지 사용 예시) : ⬇️
                link_html = f'<a href="{url}" target="_blank" rel="noopener noreferrer">⬇️ Download</a>'
            else:
                link_html = "N/A"
            download_links.append(link_html)

        df["Download"] = download_links

        # 3) DataFrame 렌더링 (HTML 링크 허용)
        # st.dataframe()은 HTML 링크를 클릭할 수 없으므로,
        # st.markdown(df.to_html(...), unsafe_allow_html=True)를 사용
        st.markdown(df.to_html(escape=False), unsafe_allow_html=True)
    else:
        st.write("아직 업로드된 파일이 없습니다.")

    # 체크리스트
    st.write("---")
    st.subheader("업로드 전 확인 사항")
    st.write("업로드 시 서비스 중인 모델에 즉시 영향을 미칩니다. **확인 후 업로드해주세요.**")
    cb_url = st.checkbox("파일 가장 앞에 url을 작성했나요? (docx)")
    cb_truth = st.checkbox("파일에 거짓 내용이 없는지 확인하였나요?")
    cb_duplicate = st.checkbox("기존에 업로드되지 않은 파일임을 확인하였나요?")

    # 다중 파일 업로더
    uploaded_files = st.file_uploader(
        label="",
        type=["pdf", "docx"],
        accept_multiple_files=True,
        key="file_uploader"
    )

    # 업로드 버튼
    if st.button("Upload"):
        # 체크리스트 확인
        if not (cb_url and cb_truth and cb_duplicate):
            st.warning("체크리스트를 모두 확인해 주세요!")
            return

        if not uploaded_files:
            st.warning("업로드할 파일을 선택해 주세요.")
            return

        # 이미 존재하는 파일명 체크
        collision_names = [f.name for f in uploaded_files if f.name in existing_files]
        if collision_names:
            st.warning(
                "다음 파일은 이미 존재합니다:\n"
                + "\n".join(f"- {name}" for name in collision_names)
                + "\n\n업로드를 건너뜁니다."
            )

        # 겹치지 않는 파일만 실제 업로드
        files_to_upload = [f for f in uploaded_files if f.name not in existing_files]

        if files_to_upload:
            with st.spinner("업로드 중입니다... 잠시만 기다려 주세요."):
                # 1. S3 업로드
                upload_s3(
                    files=files_to_upload,
                    access_key=access_key,
                    secret_key=secret_key,
                    region_name=POSTECH_REGION_NAME,
                    bucket_name=POSTECH_BUCKET_NAME,
                    prefix="uploaded/"
                )

                # 2. Local 저장
                tmp_dir = "./data/tmp"
                if not os.path.exists(tmp_dir):
                    os.makedirs(tmp_dir)

                local_file_paths = []
                for f in files_to_upload:
                    local_path = f"{tmp_dir}/{f.name[:50]}"
                    with open(local_path, "wb") as out:
                        out.write(f.getvalue())
                    local_file_paths.append(local_path)

            with st.spinner("Qdrant 업로드 중입니다... 창을 종료하지 마세요."):
                # 3. Qdrant 업로드
                upload(
                    db_path=tmp_dir,
                    recreate=False, 
                    dev=False
                )

                for file in os.listdir(tmp_dir):
                    file_path = os.path.join(tmp_dir, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)

            st.success("파일 업로드가 완료되었습니다!")
            st.rerun()
        else:
            st.info("업로드할 새로운 파일이 없습니다.")

if __name__ == "__main__":
    make_page()