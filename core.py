import streamlit as st
import asyncio, time
from src.llm.gpt.inference import run_gpt
from src.llm.gemini.inference import run_gemini_stream
from src.search.search import search
from common.types import intlist_struct, str_struct
from common.config import COLLECTION_NAME


def stream_caption(placeholder, text: str, delay: float = 0.05):
    """
    text를 한 글자씩 순차적으로 placeholder.caption()을 통해 업데이트 (가짜 스트리밍).
    """
    displayed_text = ""
    for char in text:
        displayed_text += char
        placeholder.caption(displayed_text)
        time.sleep(delay)

def chunk_text_in_subchunks(text: str, chunk_size: int = 10):
    """
    text를 chunk_size 글자씩 잘라서 yield 해주는 간단한 제너레이터
    """
    for i in range(0, len(text), chunk_size):
        yield text[i:i+chunk_size]


def get_response(
    prompt: str,
    messages: list,
    name_source_mapping: dict,
    filter: list[str] = None,
    top_k: int = 30,
    refinement_model: str = "gpt-4o-mini",
    reranking_model: str = "gpt-4o-2024-08-06",
    branch: str = "postech"
) -> str:
    """
    RAG + LLM 전체 로직을 처리해 최종 답변 문자열을 반환
    
    1. Query Refinement
    2. RAG 검색
    3. Re-ranking
    4. 최종 RAG 컨텍스트 구성 후 LLM 스트리밍 (Gemini)
    """
    try:
        # (1) Query Refinement
        start_time = time.time()
        refinement_placeholder = st.empty()
        stream_caption(refinement_placeholder, "질의를 정제 중입니다...", 0.01)
        
        refinement = run_gpt(
            target_prompt=str(prompt),
            prompt_in_path="query_refinement.json",
            gpt_model=refinement_model,
            output_structure=str_struct
        )
        refined_prompt = refinement.output

        # 대화 히스토리 정리
        history_text = ""
        for msg in messages[:-1]:
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                history_text += f"User: {content}\n"
            elif role == "assistant":
                history_text += f"Assistant: {content}\n"

        # (2) RAG 검색
        stream_caption(refinement_placeholder, "문서를 탐색 중입니다...", 0.01)
        collection_name = COLLECTION_NAME[branch]["prod"]
        found_chunks = search(
            collection_name=collection_name, 
            user_query=refined_prompt, 
            top_k=top_k, 
            filter=filter,
            dev=False
        )

        # (3) Re-ranking
        stream_caption(refinement_placeholder, "문서를 재정렬 중입니다...", 0.01)
        chunk_dict = {
            c["id"]: (c["doc_title"], c["summary"])
            for c in found_chunks
        }

        # "답변을 생성 중입니다..." 만 표시
        stream_caption(refinement_placeholder, "답변을 생성 중입니다...", 0.01)

        reranked_output = run_gpt(
            target_prompt=str(chunk_dict),
            prompt_in_path="reranking.json",
            gpt_model=reranking_model,
            output_structure=intlist_struct
        )
        reranked_ids = reranked_output.output

        filtered_chunks = [c for c in found_chunks if c["id"] in reranked_ids]
        id_to_rank = {id_: idx for idx, id_ in enumerate(reranked_ids)}
        sorted_chunks = sorted(filtered_chunks, key=lambda x: id_to_rank[x["id"]])

        # (4) 최종 RAG 컨텍스트 구성
        context_texts = [c["raw_text"] for c in sorted_chunks]
        rag_context = "\n".join(context_texts)
        final_prompt = f"""
아래는 이전 대화의 기록입니다:
{history_text}

다음은 참고 자료(RAG)에서 발췌한 내용입니다:
{rag_context}

이제 사용자의 질문을 다시 안내해 드리겠습니다:

질문: {refined_prompt}

위 대화와 자료를 기반으로 답변을 작성해 주세요.
답변:
"""

        # (4-2) 최종 답변 스트리밍
        # start_time을 넘겨주고, 첫 토큰이 오면 그 시점에 time_spent 계산
        return run_final_llm_stream(
            final_prompt=final_prompt,
            sorted_chunks=sorted_chunks,
            name_source_mapping=name_source_mapping,
            branch=branch,
            start_time=start_time,
            refinement_placeholder=refinement_placeholder
        )

    except Exception as e:
        raise Exception(f"응답 생성 중 오류가 발생했습니다: {str(e)}")


def run_final_llm_stream(
    final_prompt: str,
    sorted_chunks: list,
    name_source_mapping: dict,
    branch: str,
    start_time: float,
    refinement_placeholder: st.delta_generator.DeltaGenerator
) -> str:
    """
    최종 LLM 스트리밍을 수행하고, 완료된 결과를 반환.
    + 첫 토큰 도착 순간 => "XX초 동안 문서 탐색" 표시 (start_time 기준)
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def _streaming_call():
        message_placeholder = st.empty()
        reference_placeholder = st.empty()

        stream = await run_gemini_stream(
            target_prompt=final_prompt,
            prompt_in_path="chat_basic.json"
        )

        full_response = ""
        first_chunk_flag = True

        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content is not None:
                if first_chunk_flag:
                    # 첫 토큰이 들어온 시점 -> 여기서 시간 측정
                    first_chunk_flag = False
                    time_spent = time.time() - start_time
                    sec_spent_str = f"{int(time_spent)+1}초 동안 문서 탐색"
                    # "\n" 붙여서 줄바꿈 후 출력
                    stream_caption(refinement_placeholder, f"\n{sec_spent_str}", 0.01)

                # 본문 스트리밍
                full_response += content
                message_placeholder.markdown(full_response)

        # 출처 표시 (가짜 스트리밍)
        if sorted_chunks:
            # 중복 제거
            dedup_set = set()
            for c in sorted_chunks:
                doc_title = c.get("doc_title", "Untitled")
                doc_source = c.get("doc_source", "Unknown Source")
                if not doc_source.startswith("http"):
                    doc_source = name_source_mapping[branch].get(doc_title, doc_source)
                page_num = c.get("page_num", None)
                dedup_set.add((doc_title, doc_source, page_num))

            refs = []
            for idx, (title, source, page) in enumerate(dedup_set, start=1):
                if source.startswith("http"):
                    if page is not None:
                        refs.append(f"- **{title}** (p.{page}) / [링크로 이동]({source})")
                    else:
                        refs.append(f"- **{title}** / [링크로 이동]({source})")
                else:
                    truncated_source = source if len(source) <= 50 else source[:47] + "..."
                    if page is not None:
                        refs.append(f"- **{title}** (p.{page}) / {truncated_source}")
                    else:
                        refs.append(f"- **{title}** / {truncated_source}")
            refs_text = "\n".join(refs)

            # (A) 임시 Expander (펼쳐진 상태) 안에서 스트리밍
            expander_placeholder = reference_placeholder.empty()
            with expander_placeholder.expander("참고 자료 출처", expanded=True):
                ref_stream_placeholder = st.empty()
                displayed = ""
                for subchunk in chunk_text_in_subchunks(refs_text, chunk_size=8):
                    displayed += subchunk
                    ref_stream_placeholder.markdown(displayed)
                    time.sleep(0.01)
                time.sleep(0.2)


        return full_response

    final_answer = loop.run_until_complete(_streaming_call())
    return final_answer