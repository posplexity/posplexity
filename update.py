from tqdm import tqdm
from qdrant_client import models
from qdrant_client.models import PointStruct, ScrollResult
from common.types import Document, str_struct
from common.globals import qdrant_client
from common.config import (
    POSTECH_COLLECTION_EXP,
    POSTECH_COLLECTION_PROD,
    MAX_CHUNK_LENGTH,
    EMBED_BATCH_SIZE,
)
from src.llm.gpt.inference import async_run_gpt
from src.rag.parse import parse_word, parse_pdf, parse_mbox  
from src.rag.chunk import chunk_word, chunk_pdf, chunk_text  
from src.rag.embedding import async_openai_embedding
from src.utils.utils import async_wrapper

import os, asyncio


def get_max_point_id(collection_name: str) -> int:
    """
    해당 collection에 존재하는 Point 중 가장 큰 ID를 반환.
    만약 컬렉션이 비어있으면 0을 반환.
    """
    max_id = 0
    scroll_offset = None

    while True:
        # 한 번에 100개씩 스크롤
        result: ScrollResult = qdrant_client.scroll(
            collection_name=collection_name,
            offset=scroll_offset,
            limit=100,
            with_vectors=False,
        )
        for point in result[0]:
            if point.id > max_id:
                max_id = point.id

        if result[1] is None:
            break
        scroll_offset = result[1]

    return max_id


def upload(db_path: str, recreate: bool = False, dev: bool = True):
    """
    기존에 있던 vector ID와 겹치지 않도록,
    가장 큰 Point ID 다음부터 사용해서 새 Document를 업로드한다.
    """
    # dev / prod
    if dev:
        COLLECTION_NAME = POSTECH_COLLECTION_EXP
    else:
        COLLECTION_NAME = POSTECH_COLLECTION_PROD

    # 1. recreate_collection
    if recreate:
        qdrant_client.recreate_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=3072,
                distance=models.Distance.COSINE
            ),
        )

    # 1-1. 기존에 있는 최대 ID 구하기 (컬렉션이 비어 있으면 0)
    existing_max_id = get_max_point_id(COLLECTION_NAME)
    next_doc_id_start = (existing_max_id // 1000) + 1

    # 2. load file list
    paths_list = []
    docs_list = []

    for file in os.listdir(db_path):
        # .docx, .pdf, .mbox 모두 처리
        if file.endswith(".docx") or file.endswith(".pdf") or file.endswith("mbox"):
            paths_list.append(os.path.join(db_path, file))

    # 3. parse files
    #    파일 형식별로 parse
    for file_path in paths_list:
        if file_path.endswith(".docx"):
            doc = Document(**parse_word(file_path))
            doc.doc_type = "word"
            docs_list.append(doc)
        elif file_path.endswith(".pdf"):
            doc = Document(**parse_pdf(file_path))
            doc.doc_type = "pdf"
            docs_list.append(doc)
        elif file_path.endswith("mbox"):
            # parse_mbox()는 여러 메일(Document)들을 반환하므로 반복 처리
            mbox_docs = parse_mbox(file_path)
            for d in mbox_docs:
                d.doc_type = "mbox"
                docs_list.append(d)

    # 4. chunk files
    for doc in docs_list:
        if doc.doc_type == "word":
            doc.chunk_list = chunk_word(doc)
        elif doc.doc_type == "pdf":
            doc.chunk_list = chunk_pdf(doc)
        elif doc.doc_type == "mbox":
            # 단순 텍스트를 chunking
            doc.chunk_list = chunk_text(doc)

    # 5. 문서별로 doc_id 할당
    for i, doc in enumerate(docs_list):
        doc.doc_id = next_doc_id_start + i

    # doc & chunk 쌍 만들기
    doc_chunk_pairs = []
    for doc in docs_list:
        for chunk in doc.chunk_list:
            doc_chunk_pairs.append((doc, chunk))

    total_chunks = len(doc_chunk_pairs)

    with tqdm(total=total_chunks, desc="Making embeddings...") as pbar:
        for start_idx in range(0, total_chunks, EMBED_BATCH_SIZE):
            batch = doc_chunk_pairs[start_idx : start_idx + EMBED_BATCH_SIZE]

            breakpoint()

            # (a) 임베딩 생성
            embedding_tasks = [async_openai_embedding(chunk.body) for (_, chunk) in batch]
            embedding_results = asyncio.run(async_wrapper(embedding_tasks))

            # (a-1) 요약 생성
            summary_tasks = [async_run_gpt(chunk.body, "make_summary.json", str_struct) for (_, chunk) in batch]
            summary_results = asyncio.run(async_wrapper(summary_tasks))

            breakpoint()

            # (b) PointStruct 리스트 만들기
            batch_points = []
            for (doc, chunk), emb, summ in zip(batch, embedding_results, summary_results):
                # 임베딩 저장
                chunk.embedding = emb
                limited_text = chunk.body[:MAX_CHUNK_LENGTH]

                # ID를 생성 -> doc_id * 1000 + chunk_id
                point_id = doc.doc_id * 1000 + chunk.chunk_id

                payload_data = {
                    "doc_title": doc.doc_title,
                    "doc_source": doc.doc_source,
                    "raw_text": limited_text,
                    "summary": summ,  # 새로 생성한 요약
                }

                batch_points.append(
                    PointStruct(
                        id=point_id,
                        vector=chunk.embedding,
                        payload=payload_data,
                    )
                )

            # (c) upsert
            try:
                qdrant_client.upsert(
                    collection_name=COLLECTION_NAME,
                    points=batch_points
                )
                pbar.update(len(batch_points))
            except:
                # 만약 대량 업서트에서 에러 발생 시, 5개씩 잘라서 업서트
                for small_start_idx in range(0, len(batch_points), 5):
                    small_batch = batch_points[small_start_idx : small_start_idx + 5]
                    qdrant_client.upsert(
                        collection_name=COLLECTION_NAME,
                        points=small_batch
                    )
                    pbar.update(len(small_batch))


if __name__ == "__main__":
    # 예시 실행
    # 1) recreate=True => 컬렉션 재생성, 그리고 업로드
    #    이 경우에도 ID는 항상 0부터 다시 시작
    # upload(db_path="db/uploaded", recreate=True, dev=False)

    # 2) update => 이미 컬렉션에 데이터가 있는 경우
    #    새로 업로드될 문서들의 doc_id는 기존 max_id // 1000 + 1부터
    upload(db_path="/Users/huhchaewon/data/ 2.mbox", recreate=False, dev=False)