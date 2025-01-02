from typing import List, Dict, Any

from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue
from qdrant_client.http.models import ScoredPoint

from common.globals import qdrant_client
from src.rag.embedding import openai_embedding


def search(
    collection_name: str,
    user_query: str,
    top_k: int = 5,
    filter: List[str] = None,
    dev: bool = True
) -> List[Dict[str, Any]]:
    """
    Qdrant에서 user_query와 가장 유사한 청크들을 검색하여 반환하는 함수.
    - filter 목록에 있는 doc_source 값을 must_not 처리하여 결과에서 제외한다.
    """
    # 1. 사용자 질의 임베딩
    query_vector = openai_embedding(user_query)

    # 2. filter 구성 (must_not 조건)
    qdrant_filter = None
    if filter:  # filter가 비어있지 않다면
        # doc_source가 filter 목록에 속해있는 경우, must_not 처리
        must_not_conditions = [
            FieldCondition(
                key="filter",
                match=MatchValue(value=f)
            )
            for f in filter
        ]
        qdrant_filter = Filter(must_not=must_not_conditions)

    # 3. Qdrant 검색
    results: List[ScoredPoint] = qdrant_client.search(
        collection_name=collection_name,
        query_vector=query_vector,
        limit=top_k,
        with_payload=True,
        # query_filter=qdrant_filter,  # 구성한 filter 추가
    )

    # 4. 결과 정리
    found_chunks = []
    for r in results:
        found_chunks.append({
            "id": r.id,
            "score": r.score,
            "doc_title": r.payload.get("doc_title"),
            "doc_source": r.payload.get("doc_source"),
            "raw_text": r.payload.get("raw_text"),
            # summary가 없는 경우 대비
            "summary": r.payload.get("summary", {}).get("output", "")
        })
    return found_chunks