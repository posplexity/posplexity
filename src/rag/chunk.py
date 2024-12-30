# chunk.py
from typing import List, Dict, Any
from common.config import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_STEP
from common.types import Chunk

def sliding_window(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, chunk_step: int = DEFAULT_CHUNK_STEP) -> List[str]:
    """
    슬라이딩 윈도우 방식을 사용하여 텍스트를 청크로 분할하는 함수.
    
    :param text: 청크로 분할할 원본 텍스트
    :param chunk_size: 각 청크의 최대 문자 수
    :param chunk_step: 다음 청크를 시작할 문자 오프셋
    :return: 청크 리스트
    """
    chunks = []
    text_length = len(text)
    start = 0

    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk.strip())
        start += chunk_step

    return chunks

def chunk_word(parsed_dict: Dict[str, Any], chunk_size: int = DEFAULT_CHUNK_SIZE, chunk_step: int = DEFAULT_CHUNK_STEP) -> None:
    """
    Word(docx) 파일의 파싱 데이터를 슬라이딩 윈도우 방식으로 청킹하는 함수.
    페이지 구분 없이 전체 텍스트를 대상으로 청킹을 수행.
    
    :param parsed_dict: parse_word 함수에서 반환된 파싱된 데이터 딕셔너리
    :param chunk_size: 각 청크의 최대 문자 수
    :param chunk_step: 다음 청크를 시작할 문자 오프셋
    """
    raw_text = parsed_dict.raw_text
    chunks = sliding_window(raw_text, chunk_size, chunk_step)
    chunk_list = [Chunk(doc_id=parsed_dict.doc_id, chunk_id=idx, body=chunk) for idx, chunk in enumerate(chunks)]

    return chunk_list

def chunk_pdf(parsed_dict: Dict[str, Any], chunk_size: int = DEFAULT_CHUNK_SIZE, chunk_step: int = DEFAULT_CHUNK_STEP) -> None:
    """
    PDF 파일의 파싱 데이터를 슬라이딩 윈도우 방식으로 청킹하는 함수.
    각 페이지를 기준으로 청킹을 수행하여 페이지 간의 구분을 유지.
    
    :param parsed_dict: parse_pdf 함수에서 반환된 파싱된 데이터 딕셔너리
    :param chunk_size: 각 청크의 최대 문자 수
    :param chunk_step: 다음 청크를 시작할 문자 오프셋
    """
    raw_text = parsed_dict.raw_text
    
    # 페이지별로 텍스트를 분리 (<PAGE_BREAK: 페이지 번호>로 분리)
    pages = raw_text.split("<PAGE_BREAK:")  # 페이지 구분 기호로 분리
    chunks = []
    
    for page in pages:
        # 페이지 구분 기호가 포함되어 있을 경우 제거
        page = page.strip()
        if not page:
            continue
        # 페이지 번호 제거 (예: "1>" 또는 " 1>")
        page = page.split('>')[-1].strip()
        if not page:
            continue
        
        # 슬라이딩 윈도우 청킹
        page_chunks = sliding_window(page, chunk_size, chunk_step)
        chunks.extend(page_chunks)
    
    chunk_list = [Chunk(doc_id=parsed_dict.doc_id, chunk_id=idx, body=chunk) for idx, chunk in enumerate(chunks)]
    return chunk_list
