import os
import asyncio
from tqdm import tqdm

from qdrant_client import models
from qdrant_client.models import PointStruct

from common.types import Document, Chunk
from common.globals import qdrant_client
from common.config import COLLECTION_NAME

from src.rag.parse import parse_word, parse_pdf
from src.rag.chunk import chunk_word, chunk_pdf
from src.rag.embedding import async_openai_embedding  # 비동기 임베딩 함수
from src.utils.utils import async_wrapper  # async_wrapper(tasks) -> asyncio.gather

# 최대 저장할 청크 텍스트 길이 제한 (문자 수)
MAX_CHUNK_LENGTH = 1000

def init(db_path: str):
    # 1. recreate_collection
    qdrant_client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(
            size=3072, distance=models.Distance.COSINE
        ),
    )

    # 2. 파일 목록 로딩
    paths_list, docs_list = [], []
    for file in os.listdir(db_path):
        if file.endswith('.docx') or file.endswith('.pdf'):
            paths_list.append(os.path.join(db_path, file))

    # 3. 파일 파싱
    for idx, file_path in enumerate(paths_list):
        if file_path.endswith('.docx'):
            doc = Document(**parse_word(file_path))
            doc.doc_type = "word"
        elif file_path.endswith('.pdf'):
            doc = Document(**parse_pdf(file_path))
            doc.doc_type = "pdf"
        doc.doc_id = idx
        docs_list.append(doc)

    # 4. 청킹
    for doc in docs_list:
        if doc.doc_type == "word":
            doc.chunk_list = chunk_word(doc)
        elif doc.doc_type == "pdf":
            doc.chunk_list = chunk_pdf(doc)

    # 5. 임베딩 비동기 병렬 처리 + 업서트
    doc_chunk_pairs = []
    for doc in docs_list:
        for chunk in doc.chunk_list:
            doc_chunk_pairs.append((doc, chunk))

    total_chunks = len(doc_chunk_pairs)
    EMBED_BATCH_SIZE = 50  # 50개씩 나눠서 병렬 처리

    points = []
    with tqdm(total=total_chunks, desc="Making embeddings...") as pbar:
        for i in range(0, total_chunks, EMBED_BATCH_SIZE):
            batch = doc_chunk_pairs[i : i + EMBED_BATCH_SIZE]

            # 비동기 임베딩 요청
            tasks = [async_openai_embedding(chunk.body) for (_, chunk) in batch]
            results = asyncio.run(async_wrapper(tasks))  # [embedding, ...]

            # 결과를 청크에 반영
            for (doc, chunk), emb in zip(batch, results):
                chunk.embedding = emb

                # 최대 길이 제한
                limited_text = chunk.body[:MAX_CHUNK_LENGTH]

                # doc_source가 너무 길면 간단히 처리 (예: 파일명만)
                point_id = doc.doc_id * 1000 + chunk.chunk_id

                payload_data = {
                    "doc_title": doc.doc_title[:100],  # 너무 길면 100자만
                    "doc_source": doc.doc_source,         # 긴 경로 대신 베이스네임
                    "raw_text": limited_text            # 길이 제한된 청크 텍스트
                }

                points.append(
                    PointStruct(
                        id=point_id,
                        vector=chunk.embedding,
                        payload=payload_data
                    )
                )

            pbar.update(len(batch))

    # 6. Qdrant 업서트
    qdrant_client.upsert(
        collection_name=COLLECTION_NAME,
        points=points
    )

if __name__ == "__main__":
    init(db_path="db")