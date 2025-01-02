# everytime.py

import os
import json
import asyncio

from tqdm import tqdm

# ===== Qdrant & 관련 함수들 import =====
from common.globals import qdrant_client
from qdrant_client import models
from qdrant_client.models import PointStruct, ScrollResult

# ===== 타입/함수들 import (upload.py에서 사용하던 것) =====
from common.config import (
    POSTECH_COLLECTION_EXP,
    POSTECH_COLLECTION_PROD,
    EMBED_BATCH_SIZE,
)
from src.llm.gpt.inference import async_run_gpt
from src.rag.embedding import async_openai_embedding
from common.types import str_struct
from src.utils.utils import async_wrapper


def get_max_point_id(collection_name: str) -> int:
    """
    해당 collection에 존재하는 Point 중 가장 큰 ID를 반환.
    만약 컬렉션이 비어있으면 0을 반환.
    """
    max_id = 0
    scroll_offset = None

    # 한번에 1000개씩 스크롤
    while True:
        result: ScrollResult = qdrant_client.scroll(
            collection_name=collection_name,
            offset=scroll_offset,
            limit=1000,
            with_vectors=False,
        )
        for point in result[0]:
            if point.id > max_id:
                max_id = point.id

        if result[1] is None:
            break
        scroll_offset = result[1]

    return max_id


def get_everytime_data():
    """
    bin/everytime/free.jsonl 파일에 들어있는 
    게시글(및 댓글들)을 리스트 형태로 반환
    """
    full_data = []
    with open("bin/everytime/free.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            full_data.append(data)

    return full_data


def parse_pretty(data):
    """
    에브리타임 댓글 형식을 사람이 보기 편한 문자열로 변환.
    + doc_title, doc_source 등을 함께 반환
    """
    formatted_comments = []
    comment_num = 1

    for comment in data["comments"]:
        if comment["parent_id"] == "0":  # 메인 댓글
            formatted_comments.append(f"{comment_num}. {comment['text']}")
            # 해당 메인 댓글의 대댓글 찾기
            reply_num = 1
            for reply in data["comments"]:
                if reply["parent_id"] == comment["comment_id"]:
                    formatted_comments.append(f"{comment_num}-{reply_num}. {reply['text']}")
                    reply_num += 1
            comment_num += 1

    comments = "\n".join(formatted_comments)
    
    payload_data = {
        "doc_title": data["title"],
        "doc_source": data["url"],
        "raw_text": data["title"] + "\n" + data["content"] + "\n" + comments,
    }
    return payload_data


def upload_everytime_data(dev: bool = True):
    """
    에브리타임 데이터를 읽어서 요약/임베딩 후 Qdrant에 업서트한다.
    (일회성 사용을 가정)
    """
    # 0. 어떤 컬렉션에 업로드할지 결정 (dev / prod)
    if dev:
        COLLECTION_NAME = POSTECH_COLLECTION_EXP
    else:
        COLLECTION_NAME = POSTECH_COLLECTION_PROD

    # 1. Qdrant 컬렉션에서 현재 존재하는 max point ID 찾기
    existing_max_id = get_max_point_id(COLLECTION_NAME)
    next_doc_id_start = (existing_max_id // 1000) + 1

    # 2. 에브리타임 데이터 읽기
    data_list = get_everytime_data()

    # 3. 각 json에 대해 parse_pretty를 거쳐야 할 정보를 추출
    #    doc_id를 next_doc_id_start + i 로 지정 (한 게시글 = 하나의 문서)
    doc_info_list = []
    for i, item in enumerate(data_list):
        doc_id = next_doc_id_start + i
        parsed = parse_pretty(item)  # title, source, raw_text
        doc_info_list.append({
            "doc_id": doc_id,
            "title": parsed["doc_title"],
            "source": parsed["doc_source"],
            "body": parsed["raw_text"],   # 임베딩/요약 대상
        })

    # 4. batch 단위로 임베딩 + 요약 + 업서트
    total_docs = len(doc_info_list)
    with tqdm(total=total_docs, desc="Embedding & Summarizing") as pbar:
        for start_idx in range(0, total_docs, EMBED_BATCH_SIZE):
            batch = doc_info_list[start_idx : start_idx + EMBED_BATCH_SIZE]

            # (a) 임베딩 생성 (비동기)
            embedding_tasks = [async_openai_embedding(item["body"]) for item in batch]
            embedding_results = asyncio.run(async_wrapper(embedding_tasks))

            # (b) 요약 생성 (비동기)
            summary_tasks = [async_run_gpt(item["body"], "make_summary.json", str_struct) for item in batch]
            summary_results = asyncio.run(async_wrapper(summary_tasks))

            # (c) Qdrant 업서트할 PointStruct 리스트 만들기
            points_to_upsert = []
            for (item, emb, summ) in zip(batch, embedding_results, summary_results):
                # ID = doc_id * 1000 (chunk_id = 0 가정)
                point_id = item["doc_id"] * 1000

                payload_data = {
                    "doc_title": item["title"],
                    "doc_source": item["source"],
                    "raw_text": item["body"],   # 원문 (길면 잘라서 저장하는 것도 가능)
                    "summary": summ,
                    "filter":"everytime"
                }

                points_to_upsert.append(
                    PointStruct(
                        id=point_id,
                        vector=emb, 
                        payload=payload_data
                    )
                )

            # (d) 업서트 실행
            try:
                qdrant_client.upsert(
                    collection_name=COLLECTION_NAME,
                    points=points_to_upsert
                )
                pbar.update(len(points_to_upsert))
            except:
                # 혹시 대량 업서트 에러 시, 소규모로 재시도
                for small_start in range(0, len(points_to_upsert), 5):
                    small_batch = points_to_upsert[small_start : small_start + 5]
                    qdrant_client.upsert(
                        collection_name=COLLECTION_NAME,
                        points=small_batch
                    )
                    pbar.update(len(small_batch))


if __name__ == "__main__":
    # 원하는 모드로 실행하면 됩니다.
    # dev=True  => POSTECH_COLLECTION_EXP 컬렉션에 업서트
    # dev=False => POSTECH_COLLECTION_PROD 컬렉션에 업서트
    upload_everytime_data(dev=False)

    # 혹은 테스트만 간단히 하고 싶다면:
    # data = get_everytime_data()
    # parsed_example = parse_pretty(data[0])
    # print(parsed_example)