from tqdm import tqdm
from qdrant_client import models
from qdrant_client.models import PointStruct

from common.types import Document
from common.globals import qdrant_client
from common.config import COLLECTION_NAME_EXP, COLLECTION_NAME_PROD, MAX_CHUNK_LENGTH, EMBED_BATCH_SIZE
from src.rag.parse import parse_word, parse_pdf
from src.rag.chunk import chunk_word, chunk_pdf
from src.rag.embedding import async_openai_embedding  
from src.utils.utils import async_wrapper 

import os, asyncio


def upload(db_path: str, recreate:bool=False, dev:bool=True):
    # dev / prod
    if dev:
        COLLECTION_NAME = COLLECTION_NAME_EXP
    else:
        COLLECTION_NAME = COLLECTION_NAME_PROD

    # 1. recreate_collection
    if recreate:
        qdrant_client.recreate_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=3072, 
                distance=models.Distance.COSINE
            ),
        )

    # 2. load file list
    paths_list, docs_list = [], []
    for file in os.listdir(db_path):
        if file.endswith('.docx') or file.endswith('.pdf'):
            paths_list.append(os.path.join(db_path, file))

    # 3. parse files
    for idx, file_path in enumerate(paths_list):
        if file_path.endswith('.docx'):
            doc = Document(**parse_word(file_path))
            doc.doc_type = "word"
        elif file_path.endswith('.pdf'):
            doc = Document(**parse_pdf(file_path))
            doc.doc_type = "pdf"
        doc.doc_id = idx
        docs_list.append(doc)

    # 4. chunk files
    for doc in docs_list:
        if doc.doc_type == "word":
            doc.chunk_list = chunk_word(doc)
        elif doc.doc_type == "pdf":
            doc.chunk_list = chunk_pdf(doc)

    # 5. upload vectors
    doc_chunk_pairs = []
    for doc in docs_list:
        for chunk in doc.chunk_list:
            doc_chunk_pairs.append((doc, chunk))

    total_chunks = len(doc_chunk_pairs)

    with tqdm(total=total_chunks, desc="Making embeddings...") as pbar:
        for start_idx in range(0, total_chunks, EMBED_BATCH_SIZE):
            batch = doc_chunk_pairs[start_idx : start_idx + EMBED_BATCH_SIZE]

            # (a) make embeddings
            tasks = [async_openai_embedding(chunk.body) for (_, chunk) in batch]
            results = asyncio.run(async_wrapper(tasks))  # [embedding, ...]

            # (b) make points
            batch_points = []
            for (doc, chunk), emb in zip(batch, results):
                chunk.embedding = emb
                limited_text = chunk.body[:MAX_CHUNK_LENGTH]

                point_id = doc.doc_id * 1000 + chunk.chunk_id
                payload_data = {
                    "doc_title": doc.doc_title,  
                    "doc_source": doc.doc_source,    
                    "raw_text": limited_text
                }
                batch_points.append(
                    PointStruct(
                        id=point_id,
                        vector=chunk.embedding,
                        payload=payload_data
                    )
                )

            # (c) upload vectors
            try:
                qdrant_client.upsert(
                    collection_name=COLLECTION_NAME,
                    points=batch_points
                )
                pbar.update(len(batch_points))

            except:
                for small_start_idx in range(0, len(batch_points), 5):
                    small_batch = batch_points[small_start_idx : small_start_idx + 5]
                    qdrant_client.upsert(
                        collection_name=COLLECTION_NAME,
                        points=small_batch
                    )
                    pbar.update(len(small_batch))

if __name__ == "__main__":
    # init
    upload(db_path="db/uploaded", recreate=True)

    # update
    # upload(db_path="db/staged", recreate=False, dev=False)