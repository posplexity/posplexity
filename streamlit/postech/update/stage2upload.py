import sys, os
sys.path.append(os.path.abspath("")) 

from dotenv import load_dotenv
from src.utils import upload_s3  # 이미 작성된 업로드 함수 (copy/move 등을 활용)
from common.config import POSTECH_BUCKET_NAME, POSTECH_REGION_NAME

import streamlit as st
from botocore.exceptions import ClientError

import PyPDF2, docx, boto3, io

load_dotenv()

def list_staged_files(bucket_name, region_name, access_key, secret_key, prefix="staged"):
    """
    S3 버킷 내 특정 prefix(폴더)에 있는 파일(Key) 목록을 반환하는 함수.
    예: prefix="staged" => "mybucket/staged/..." 내 파일만 가져오기
    """
    s3 = boto3.client(
        "s3",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region_name
    )

    file_list = []
    try:
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        if "Contents" in response:
            # 'staged/' 폴더 그 자체만 잡히는 경우도 있으므로, Key != prefix 조건으로 필터링
            file_list = [obj["Key"] for obj in response["Contents"] if obj["Key"] != prefix]
    except ClientError as e:
        st.error(f"S3 파일 목록 조회 실패: {e}")
    
    return file_list

def download_s3_file(bucket_name, region_name, access_key, secret_key, key):
    """
    S3에서 지정한 key 파일을 바이트로 다운로드하여 반환.
    """
    s3 = boto3.client(
        "s3",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region_name
    )

    try:
        obj = s3.get_object(Bucket=bucket_name, Key=key)
        return obj["Body"].read()
    except ClientError as e:
        st.error(f"파일 다운로드 실패: {e}")
        return None

def parse_pdf(file_bytes: bytes) -> str:
    """
    PDF 바이트를 입력받아 텍스트를 추출해서 반환
    (PyPDF2)
    """
    text = ""
    try:
        with io.BytesIO(file_bytes) as pdf_file:  # 바이트를 파일 객체로 변환
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
    except Exception as e:
        text = f"[PDF 파싱 오류] {e}"
    return text

def parse_docx(file_bytes: bytes) -> str:
    """
    DOCX 바이트를 입력받아 텍스트를 추출해서 반환
    (간단 예시: python-docx)
    """
    text = ""
    try:
        # python-docx는 파일 경로만 받으므로,
        # 바이트를 임시 파일로 만들어서 open해야 함
        # 또는 io.BytesIO(file_bytes)를 바로 넘겨도 되지만, 아래 방식을 예시로 작성
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        doc = docx.Document(tmp_path)
        paragraphs = [p.text for p in doc.paragraphs]
        text = "\n".join(paragraphs)

        # 임시 파일 삭제
        os.remove(tmp_path)
    except Exception as e:
        text = f"[DOCX 파싱 오류] {e}"
    return text

def copy_s3_object(
    bucket_name,
    region_name,
    access_key,
    secret_key,
    source_key,
    target_key
):
    """
    S3 내부에서 파일을 복사하는 함수.
    copy_source = {'Bucket': bucket_name, 'Key': source_key}
    s3.copy(CopySource=copy_source, Bucket=bucket_name, Key=target_key)
    """
    s3 = boto3.client(
        "s3",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region_name
    )
    copy_source = {
        'Bucket': bucket_name,
        'Key': source_key
    }
    try:
        s3.copy_object(CopySource=copy_source, Bucket=bucket_name, Key=target_key)
        # 원본 삭제(이동)하려면 아래 주석 해제
        # s3.delete_object(Bucket=bucket_name, Key=source_key)
    except ClientError as e:
        st.error(f"S3 파일 복사 실패: {e}")
        return False
    return True

def make_page():
    st.set_page_config(page_title="Stage to Upload", layout="centered")

    st.title("Staged 파일 검토 및 업로드")
    st.caption("powered by posplexity")

    # S3 접근 정보
    access_key = os.getenv("S3_ACCESS_KEY")
    secret_key = os.getenv("S3_SECRET_ACCESS_KEY")

    # 1) 현재 'staged' 폴더에 있는 파일 목록 가져오기
    staged_files = list_staged_files(
        bucket_name=POSTECH_BUCKET_NAME,
        region_name=POSTECH_REGION_NAME,
        access_key=access_key,
        secret_key=secret_key,
        prefix="staged"
    )

    if not staged_files:
        st.info("현재 스테이징된 파일이 없습니다.")
        return

    # 2) 파일 선택 박스
    selected_file = st.selectbox("검토할 파일을 선택하세요", staged_files)

    # 3) "미리보기" 버튼
    if st.button("미리보기"):
        # 파일 다운로드
        file_bytes = download_s3_file(
            bucket_name=POSTECH_BUCKET_NAME,
            region_name=POSTECH_REGION_NAME,
            access_key=access_key,
            secret_key=secret_key,
            key=selected_file
        )
        if not file_bytes:
            st.error("파일 다운로드 실패 또는 파일이 없습니다.")
            return

        # 확장자에 따라 텍스트 파싱
        _, ext = os.path.splitext(selected_file.lower())
        if ext == ".pdf":
            with st.spinner("PDF 텍스트 추출 중..."):
                parsed_text = parse_pdf(file_bytes)
        elif ext == ".docx":
            with st.spinner("DOCX 텍스트 추출 중..."):
                parsed_text = parse_docx(file_bytes)
        else:
            st.warning("PDF / DOCX 형식만 지원 중입니다.")
            return

        st.subheader("문서 내용(텍스트):")
        st.write(parsed_text)

    # 4) "확정 업로드" 버튼
    st.write("---")
    if st.button("확정 업로드 (staged -> final)"):
        # 예: staged/foo.pdf -> final/foo.pdf 로 복사
        # (1) staged/... prefix 제거
        original_filename = selected_file.split("staged/")[-1]
        # (2) 최종 업로드 경로 설정
        target_key = f"final/{original_filename}"

        with st.spinner("최종 업로드(복사) 중..."):
            success = copy_s3_object(
                bucket_name=POSTECH_BUCKET_NAME,
                region_name=POSTECH_REGION_NAME,
                access_key=access_key,
                secret_key=secret_key,
                source_key=selected_file,
                target_key=target_key
            )

        if success:
            st.success(f"확정 업로드 완료: {target_key}")
            # 페이지 재실행하여 목록 갱신
            st.experimental_rerun()

if __name__ == "__main__":
    make_page()