from src.rag.parse import parse_word, parse_pdf
from src.rag.chunk import chunk_word, chunk_pdf
from src.rag.embedding import openai_embedding
from common.types import Document, Chunk
from common.globals import qdrant_client
from common.config import COLLECTION_NAME

from qdrant_client import models
from qdrant_client.models import PointStruct
import os
from tqdm import tqdm


def init(db_path: str):
    # 1. create collection
    qdrant_client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(
            size=3072, distance=models.Distance.COSINE
        ),
    )

    # 2. file load
    paths_list, docs_list = [], []
    for file in os.listdir(db_path):
        if file.endswith('.docx') or file.endswith('.pdf'):
            paths_list.append(os.path.join(db_path, file))

    # 3. file parsing
    for idx, file_path in tqdm(enumerate(paths_list), desc="Parsing files...", total=len(paths_list)):
        if file_path.endswith('.docx'):
            doc = Document(**parse_word(file_path))
            doc.doc_type = "word"
        elif file_path.endswith('.pdf'):
            doc = Document(**parse_pdf(file_path))
            doc.doc_type = "pdf"
            
        doc.doc_id = idx
        docs_list.append(doc)

    # 4. file chunking
    for doc in tqdm(docs_list, desc="Chunking files..."):
        if doc.doc_type == "word":
            doc.chunk_list = chunk_word(doc)
        elif doc.doc_type == "pdf":
            doc.chunk_list = chunk_pdf(doc)

    # 5. get embedding, upsert
    points = []
    total_chunks = sum(len(doc.chunk_list) for doc in docs_list)
    
    with tqdm(total=total_chunks, desc="Making embeddings...") as pbar:
        for doc in docs_list:
            for chunk in doc.chunk_list:
                chunk.embedding = openai_embedding(chunk.body)
                point_id = doc.doc_id*1000 + chunk.chunk_id

                payload_data = {
                    "doc_title": doc.doc_title,
                    "doc_source": doc.doc_source,
                    "raw_text": chunk.body
                }
                points.append(
                    PointStruct(
                        id=point_id,
                        vector=chunk.embedding,
                        payload=payload_data
                    )
                )
                pbar.update(1)

    qdrant_client.upsert(
        collection_name=COLLECTION_NAME,
        points=points
    )


if __name__ == "__main__":
    # upload_files(["data/test.docx"])
    init(db_path="db")