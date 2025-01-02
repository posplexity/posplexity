# chunk.py
from typing import List, Dict, Any
from common.config import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_STEP
from common.types import Chunk, Document

def sliding_window(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, chunk_step: int = DEFAULT_CHUNK_STEP) -> List[str]:
    """
    슬라이딩 윈도우 방식을 사용하여 텍스트를 청크로 분할하는 함수.
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
    """
    raw_text = parsed_dict.raw_text
    chunks = sliding_window(raw_text, chunk_size, chunk_step)
    chunk_list = [Chunk(doc_id=parsed_dict.doc_id, chunk_id=idx, body=chunk) for idx, chunk in enumerate(chunks)]

    return chunk_list

def chunk_pdf(parsed_dict: Dict[str, Any], chunk_size: int = DEFAULT_CHUNK_SIZE, chunk_step: int = DEFAULT_CHUNK_STEP) -> None:
    """
    PDF 파일의 파싱 데이터를 슬라이딩 윈도우 방식으로 청킹하는 함수.
    각 페이지를 기준으로 청킹을 수행하여 페이지 간의 구분을 유지.
    """
    raw_text = parsed_dict.raw_text
    
    # 페이지별로 텍스트를 분리 (<PAGE_BREAK: 페이지 번호>로 분리)
    pages = raw_text.split("<PAGE_BREAK:")  
    chunks = []
    
    for page in pages:
        page = page.strip()
        if not page:
            continue
        page = page.split('>')[-1].strip()
        if not page:
            continue
        
        # 슬라이딩 윈도우 청킹
        page_chunks = sliding_window(page, chunk_size, chunk_step)
        chunks.extend(page_chunks)
    
    chunk_list = [Chunk(doc_id=parsed_dict.doc_id, chunk_id=idx, body=chunk) for idx, chunk in enumerate(chunks)]
    return chunk_list

def chunk_text(doc: Document) -> list[Chunk]:
    """
    Document의 body(단순 텍스트)를 일정 길이로 잘라서 Chunk의 list로 반환.
    아래는 예시 구현이며, 실제로는 토큰 단위로 잘라내거나,
    적절한 길이(예: 1000자, 2000자 등)로 segmenting 하는 로직을 넣으시면 됩니다.
    """
    max_len = 1000  # 예시
    body = doc.raw_text

    chunks = []
    start_idx = 0
    chunk_id = 0

    while start_idx < len(body):
        end_idx = start_idx + max_len
        snippet = body[start_idx:end_idx]
        chunk = Chunk(
            doc_id=doc.doc_id,
            chunk_id=chunk_id,
            body=snippet
        )
        chunks.append(chunk)
        chunk_id += 1
        start_idx = end_idx

    return chunks