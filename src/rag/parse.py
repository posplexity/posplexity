
from typing import Dict, Any, List
from urllib.parse import urlparse
from pydantic import BaseModel
from src.llm.gpt.inference import async_run_gpt
from src.utils.utils import async_wrapper
from common.types import str_struct

from PIL import Image
import os, re, docx, pdfplumber, asyncio, io


def parse_word(file_path: str) -> Dict[str, Any]:
    """
    Word(docx) 파일을 파싱하여 title, source, raw_text를 추출하는 함수.
    - 첫 줄이 URL인 경우만 출처로 사용, 아니면 파일명을 출처로 사용
    - 모든 텍스트는 하나의 문자열로 합침
    """
    # 1) Title과 source는 파일명 그대로 사용 (확장자 포함)
    filename = os.path.basename(file_path)

    # 2) Word 파일 로딩
    doc = docx.Document(file_path)

    # 3) 전체 텍스트 파싱 + 불필요한 기호 제거
    full_text = []
    first_line = True
    
    for para in doc.paragraphs:
        raw_text = para.text.strip()
        if raw_text:
            cleaned_text = " ".join(raw_text.split())  # 공백 정리
            if first_line:  # 첫 번째 유효한 텍스트 처리
                first_line = False
                # URL인 경우만 source로 사용
                if cleaned_text.startswith(('http://', 'https://')):
                    source = cleaned_text
                    continue
                # URL이 아니면 텍스트로 처리
                cleaned_text = re.sub(r"[^0-9A-Za-z가-힣\s.,!?\-()]", "", cleaned_text)
                if cleaned_text:
                    full_text.append(cleaned_text)
            else:
                cleaned_text = re.sub(r"[^0-9A-Za-z가-힣\s.,!?\-()]", "", cleaned_text)
                if cleaned_text:
                    full_text.append(cleaned_text)

    # 4) 최종 dict 구성
    parsed_dict = {
        "doc_title": filename,
        "doc_source": source if 'source' in locals() else filename,  # URL이 없으면 파일명을 출처로
        "raw_text": " ".join(full_text),
        "chunk_list": []
    }
    return parsed_dict


import os
import re
import pdfplumber
from typing import Dict, Any
# from PIL import Image   # 필요 없다면 임포트 제거

def parse_pdf(file_path: str) -> Dict[str, Any]:
    """
    PDF 문서를 파싱하여 title, source, raw_text를 추출하는 함수.
    - 첫 줄이 URL인 경우만 출처로 사용, 아니면 파일명을 출처로 사용
    - 모든 텍스트는 하나의 문자열로 합침
    - 이미지와 관련된 코드 구조는 유지하되, 실제 바이너리는 저장하지 않음
    """
    filename = os.path.basename(file_path)
    full_text = []
    first_line = True
    source = None

    with pdfplumber.open(file_path) as pdf:
        for page_index, page in enumerate(pdf.pages):
            # (1) 텍스트 추출
            page_text = page.extract_text()
            if page_text:
                lines = page_text.split('\n')
                for line in lines:
                    cleaned_line = " ".join(line.strip().split())
                    if cleaned_line:
                        # 첫 유효 텍스트가 URL인지 확인
                        if first_line:
                            first_line = False
                            if cleaned_line.startswith(('http://', 'https://')):
                                source = cleaned_line
                                continue
                            cleaned_line = re.sub(r"[^0-9A-Za-z가-힣\s.,!?\-()]", "", cleaned_line)
                            if cleaned_line:
                                full_text.append(cleaned_line)
                        else:
                            cleaned_line = re.sub(r"[^0-9A-Za-z가-힣\s.,!?\-()]", "", cleaned_line)
                            if cleaned_line:
                                full_text.append(cleaned_line)

            # (2) 이미지 처리 구조는 남겨두지만, 실제 바이너리/설명은 스킵
            if page.images:
                # 예) 간단히 "<IMAGE>"라는 토큰만 삽입
                # (MVP 단계에서 이미지 바이너리, GPT 호출 등은 전부 스킵)
                full_text.append("<IMAGE>")

                """
                # 미래에 이미지 처리를 추가하고 싶다면:
                async_task = []
                for img in page.images:
                    # 만약 이미지 분석을 하려면:
                    # image_bytes = img.get('stream').get_data()
                    # image = Image.open(io.BytesIO(image_bytes))
                    
                    # async_task.append(
                    #     async_run_gpt(
                    #         target_prompt="",
                    #         prompt_in_path="parse_image.json",
                    #         output_structure=str_struct,
                    #         img_in_data=image,
                    #         gpt_model="gpt-4o-2024-08-06"
                    #     )
                    # )
                # results = asyncio.run(async_wrapper(async_task))
                # # <IMAGE_DESC: ...> 형태로 넣기
                # full_text.append(f"<IMAGE_DESC: {results[0].output}>")
                """

            # (3) 페이지 구분 (원치 않으면 제거 가능)
            full_text.append(f"<PAGE_BREAK: {page_index}>")

    parsed_dict = {
        "doc_title": filename,
        "doc_source": source if source else filename,  # URL이 없으면 파일명
        "raw_text": " ".join(full_text),
        "chunk_list": []  # (필요하다면 나중에 청크로 쪼개 사용)
    }
    return parsed_dict