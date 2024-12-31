import os
import asyncio
from tqdm import tqdm

from qdrant_client import models
from qdrant_client.models import PointStruct

from common.types import Document, Chunk
from common.globals import qdrant_client
from common.config import COLLECTION_NAME, MAX_CHUNK_LENGTH, EMBED_BATCH_SIZE

from src.rag.parse import parse_word, parse_pdf
from src.rag.chunk import chunk_word, chunk_pdf
from src.rag.embedding import async_openai_embedding  # 비동기 임베딩 함수
from src.utils.utils import async_wrapper  # async_wrapper(tasks) -> asyncio.gather


def init(db_path: str):
    # 1. recreate_collection
    qdrant_client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(
            size=3072, 
            distance=models.Distance.COSINE
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
    #    -> doc_chunk_pairs = [(doc, chunk), ...] 생성
    doc_chunk_pairs = []
    for doc in docs_list:
        for chunk in doc.chunk_list:
            doc_chunk_pairs.append((doc, chunk))

    total_chunks = len(doc_chunk_pairs)

    # tqdm 설정
    with tqdm(total=total_chunks, desc="Making embeddings...") as pbar:
        # 한 번에 EMBED_BATCH_SIZE 만큼 임베딩 + 업서트
        for start_idx in range(0, total_chunks, EMBED_BATCH_SIZE):
            batch = doc_chunk_pairs[start_idx : start_idx + EMBED_BATCH_SIZE]

            # (a) 비동기 임베딩
            tasks = [async_openai_embedding(chunk.body) for (_, chunk) in batch]
            results = asyncio.run(async_wrapper(tasks))  # [embedding, ...]

            # (b) batch_points 리스트 생성 (이번 배치에 해당하는 points)
            batch_points = []
            for (doc, chunk), emb in zip(batch, results):
                chunk.embedding = emb
                limited_text = chunk.body[:MAX_CHUNK_LENGTH]

                point_id = doc.doc_id * 1000 + chunk.chunk_id
                payload_data = {
                    "doc_title": doc.doc_title[:100],  # 너무 길면 100자만
                    "doc_source": doc.doc_source,       # 혹은 os.path.basename(doc.doc_source)
                    "raw_text": limited_text
                }
                batch_points.append(
                    PointStruct(
                        id=point_id,
                        vector=chunk.embedding,
                        payload=payload_data
                    )
                )

            # (c) Qdrant 업서트
            try:
                qdrant_client.upsert(
                    collection_name=COLLECTION_NAME,
                    points=batch_points
                )
                # 업서트 성공 시, tqdm 진행도 갱신
                pbar.update(len(batch_points))

            except:
                # 전체 업서트가 실패하면 5개씩 잘라서 재시도
                print(f"전체 업서트 실패. 5개씩 나눠서 시도합니다...")
                for small_start_idx in range(0, len(batch_points), 5):
                    small_batch = batch_points[small_start_idx : small_start_idx + 5]
                    try:
                        qdrant_client.upsert(
                            collection_name=COLLECTION_NAME,
                            points=small_batch
                        )
                        pbar.update(len(small_batch))
                    except Exception as e:
                        print(f"배치 {small_start_idx//5 + 1} 업서트 실패: {str(e)}")
                        breakpoint()  # 필요 시 디버깅

if __name__ == "__main__":
    init(db_path="db")