from typing import Dict, Any
import os, re, docx, pdfplumber


def parse_word(file_path: str, clean: bool = False) -> Dict[str, Any]:
    """
    Word(docx) 파일을 파싱하여 title, source, raw_text를 추출하는 함수.
    - 첫 줄이 URL인 경우만 출처로 사용, 아니면 파일명을 출처로 사용
    - 모든 텍스트는 하나의 문자열로 합침
    """
    # 1. Title, Source를 파일명 그대로 사용
    filename = os.path.basename(file_path)
    doc = docx.Document(file_path)

    # 2. 전체 데이터 파싱, 불필요한 기호 제거
    full_text = []
    first_line = True
    
    for para in doc.paragraphs:
        raw_text = para.text.strip()
        if raw_text:
            cleaned_text = " ".join(raw_text.split())  
            if first_line:  
                first_line = False
                # URL인 경우만 source로 사용
                if cleaned_text.startswith(('http://', 'https://')):
                    source = cleaned_text
                    continue
                # URL이 아니면 텍스트로 처리
                if clean:
                    cleaned_text = re.sub(r"[^0-9A-Za-z가-힣\s.,!?\-()]", "", cleaned_text)
                if cleaned_text:
                    full_text.append(cleaned_text)
            else:
                if clean:
                    cleaned_text = re.sub(r"[^0-9A-Za-z가-힣\s.,!?\-()]", "", cleaned_text)
                if cleaned_text:
                    full_text.append(cleaned_text)

    # 3. 최종 Dict 반환
    parsed_dict = {
        "doc_title": filename,
        "doc_source": source if 'source' in locals() else filename, 
        "raw_text": " ".join(full_text),
        "chunk_list": []
    }
    return parsed_dict


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
            # 1. 텍스트 추출
            page_text = page.extract_text()
            if page_text:
                lines = page_text.split('\n')
                for line in lines:
                    cleaned_line = " ".join(line.strip().split())
                    if cleaned_line:
                        # 1-1. 첫 유효 텍스트가 URL인지 확인
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

            # 2. 이미지 처리 구조는 남겨두지만, 실제 바이너리/설명은 스킵
            if page.images:
                full_text.append("<IMAGE>")

            # 3. 페이지 구분 
            full_text.append(f"<PAGE_BREAK: {page_index}>")

    # 4. 최종 Dict 반환
    parsed_dict = {
        "doc_title": filename,
        "doc_source": source if source else filename, 
        "raw_text": " ".join(full_text),
        "chunk_list": [] 
    }
    return parsed_dict