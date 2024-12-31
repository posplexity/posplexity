from common.types import Chunk
from src.rag.embedding import openai_embedding
from common.globals import qdrant_client
from common.config import COLLECTION_NAME_PROD, COLLECTION_NAME_EXP
from typing import List, Dict, Any
from qdrant_client.models import ScoredPoint
    
def search_deprecated(user_query:str, top_k:int=5, dev:bool=True) -> list[Chunk]:
    query_embedding = openai_embedding(user_query)
    hits = qdrant_client.search(
        collection_name=COLLECTION_NAME_EXP if dev else COLLECTION_NAME_PROD,
        query_vector=query_embedding,
        limit=top_k
    )

    return hits

def search(user_query: str, top_k: int = 5, dev:bool=True) -> List[Dict[str, Any]]:
    """
    Qdrant에서 user_query와 가장 유사한 청크들을 검색하여 반환하는 함수.
    """
    # 1) 사용자 질의 임베딩
    query_vector = openai_embedding(user_query)

    # 2) Qdrant 검색
    results: List[ScoredPoint] = qdrant_client.search(
        collection_name=COLLECTION_NAME_EXP if dev else COLLECTION_NAME_PROD,
        query_vector=query_vector,
        limit=top_k,
        with_payload=True
    )

    # 3) 결과 정리
    found_chunks = []
    for r in results:
        found_chunks.append({
            "id": r.id,
            "score": r.score,
            "doc_title": r.payload.get("doc_title"),
            "doc_source": r.payload.get("doc_source"),
            "raw_text": r.payload.get("raw_text"),
        })
    return found_chunks