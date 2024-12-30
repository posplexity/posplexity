
from typing import Dict, Any, List
from urllib.parse import urlparse
from pydantic import BaseModel
from src.llm.gpt.inference import async_run_gpt
from src.utils.utils import async_wrapper
from common.types import str_struct


import os, re, docx, pdfplumber, asyncio


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

def parse_pdf(file_path: str) -> Dict[str, Any]:
    """
    PDF 문서를 파싱하여 title, source, raw_text를 추출하는 함수.
    - 첫 줄이 URL인 경우만 출처로 사용, 아니면 파일명을 출처로 사용
    - 모든 텍스트는 하나의 문자열로 합침
    - 이미지가 존재하면 run_gpt()를 호출해 <IMAGE_DESC: ...> 형태로 삽입
    """
    filename = os.path.basename(file_path)
    full_text = []
    first_line = True
    source = None  # URL일 수도, 아닐 수도 있음

    with pdfplumber.open(file_path) as pdf:
        for page_index, page in enumerate(pdf.pages):
            # 1) 텍스트 추출
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
                                # 첫 줄이 URL이면 출처로 사용
                                source = cleaned_line
                                continue
                            # URL 아니면 텍스트로 처리
                            cleaned_line = re.sub(r"[^0-9A-Za-z가-힣\s.,!?\-()]", "", cleaned_line)
                            if cleaned_line:
                                full_text.append(cleaned_line)
                        else:
                            cleaned_line = re.sub(r"[^0-9A-Za-z가-힣\s.,!?\-()]", "", cleaned_line)
                            if cleaned_line:
                                full_text.append(cleaned_line)

            # 2) 이미지 확인 & GPT 호출
            if page.images:
                # 페이지에 이미지가 하나 이상 있으면
                for img in page.images:
                    async_task = []
                    breakpoint()
                    async_task.append(
                        async_run_gpt(
                            target_prompt="",
                            prompt_in_path="parse_image.json",
                            output_structure=str_struct,
                            img_in_data=img,
                            gpt_model="gpt-4o-2024-08-06"
                        )
                    )

                results = asyncio.run(async_wrapper(async_task))
                breakpoint()
                image_desc = run_gpt()
                breakpoint()
                # <IMAGE_DESC: ...> 형태로 넣기
                full_text.append(f"<IMAGE_DESC: {image_desc}>")

    parsed_dict = {
        "doc_title": filename,
        "doc_source": source if source else filename,  # URL 없으면 파일명
        "raw_text": " ".join(full_text),
        "chunk_list": []  # (필요하다면 나중에 청크로 쪼개 사용)
    }
    return parsed_dict