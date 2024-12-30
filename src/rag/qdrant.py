from qdrant_client import QdrantClient, models
from qdrant_client.http.models import SearchParams


from src.rag.parse import parse_word, parse_pdf
from src.rag.chunk import chunk_word, chunk_pdf
from src.rag.embedding import openai_embedding
from common.types import Document, Chunk

import os
from typing import List

# Qdrant 관련 임포트
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct


def upsert_chunks_to_qdrant(chunks: List[Chunk]) -> None:
    """
    추출된 청크들을 Qdrant에 업서트(Upsert)하는 함수.
    """
    # 3. PointStruct 리스트 생성
    points = []
    for idx, chunk in enumerate(chunks):
        point_id = f"{chunk.doc_id}_{getattr(chunk, 'chunk_id', idx)}"

        payload_data = {
            "doc_id": chunk.doc_id,
            "doc_source": chunk.doc_source,
            "raw_text": chunk.raw_text
        }

        points.append(
            PointStruct(
                id=point_id,
                vector=chunk.embedding,
                payload=payload_data
            )
        )

    # 4. Qdrant에 업서트
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points
    )
    print(f"[INFO] 총 {len(chunks)}개의 청크를 Qdrant에 업서트했습니다.")


def create_collection(
    qdrant_client: QdrantClient, collection_name: str, collection_size: int = 768
) -> None:
    """
    Qdrant에서 새 컬렉션을 생성합니다.
    """
    qdrant_client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(
            size=collection_size, distance=models.Distance.COSINE
        ),
    )


def delete_collection(qdrant_client: QdrantClient, collection_name: str) -> None:
    """
    Qdrant에서 특정 컬렉션을 삭제합니다.
    """
    qdrant_client.delete_collection(collection_name=collection_name)


def upsert_item_to_qdrant(
    embedding: list,
    product_id: int,
    qdrant_client: QdrantClient,
    collection_name: str,
    payload: dict = None,
) -> None:
    """
    Qdrant에 상품 이미지 embedding을 upsert 합니다.

    Args:
        embedding: 임베딩 벡터
        product_id: 상품 ID
        qdrant_client: Qdrant 클라이언트
        collection_name: 컬렉션 이름
        payload: 메타데이터 페이로드 (선택사항)
    """
    point = models.PointStruct(id=product_id, vector=embedding, payload=payload)
    qdrant_client.upsert(collection_name=collection_name, points=[point])
