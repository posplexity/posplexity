from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class Chunk(BaseModel):
    doc_id: int
    chunk_id: int
    body: str
    embedding: list[float] = []

class Document(BaseModel):
    doc_id: int = -1
    doc_type: str=""

    doc_title: str = ""
    doc_source: str = "출처를 찾지 못했습니다."
    chunk_list: list[Chunk] = []
    raw_text: str=""

class str_struct(BaseModel):
    output: str