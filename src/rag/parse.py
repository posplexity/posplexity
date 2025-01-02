from email.header import decode_header, make_header
from bs4 import BeautifulSoup
from typing import Dict, Any

from common.types import Document

import os, re, docx, pdfplumber, mailbox




def parse_word(file_path: str, clean: bool = False) -> Dict[str, Any]:
    """
    Word(docx) 파일을 파싱하여 title, source, raw_text를 추출하는 함수.
    - 첫 줄이 URL인 경우만 출처로 사용, 아니면 파일명을 출처로 사용
    - 모든 텍스트는 하나의 문자열로 합침
    """
    # 1. Title, Source를 파일명 그대로 사용
    filename = os.path.basename(file_path)
    doc = docx.Document(file_path)

    # 2. 전체 데이터 파싱, 불필요한 기호 제거
    full_text = []
    first_line = True
    
    for para in doc.paragraphs:
        raw_text = para.text.strip()
        if raw_text:
            cleaned_text = " ".join(raw_text.split())  
            if first_line:  
                first_line = False
                # URL인 경우만 source로 사용
                if cleaned_text.startswith(('URL', 'http://', 'https://')):
                    if cleaned_text.startswith('URL'):
                        source = cleaned_text.split('URL: ')[1]
                    else:
                        source = cleaned_text
                    continue
                # URL이 아니면 텍스트로 처리
                if clean:
                    cleaned_text = re.sub(r"[^0-9A-Za-z가-힣\s.,!?\-()]", "", cleaned_text)
                if cleaned_text:
                    full_text.append(cleaned_text)
            else:
                if clean:
                    cleaned_text = re.sub(r"[^0-9A-Za-z가-힣\s.,!?\-()]", "", cleaned_text)
                if cleaned_text:
                    full_text.append(cleaned_text)

    # 3. 최종 Dict 반환
    parsed_dict = {
        "doc_title": filename,
        "doc_source": source if 'source' in locals() else filename, 
        "raw_text": " ".join(full_text),
        "chunk_list": []
    }
    return parsed_dict


def parse_pdf(file_path: str) -> Dict[str, Any]:
    """
    PDF 문서를 파싱하여 title, source, raw_text를 추출하는 함수.
    - 첫 줄이 URL인 경우만 출처로 사용, 아니면 파일명을 출처로 사용
    - 모든 텍스트는 하나의 문자열로 합침
    - 이미지와 관련된 코드 구조는 유지하되, 실제 바이너리는 저장하지 않음
    """
    filename = os.path.basename(file_path)
    full_text = []
    first_line = True
    source = None

    with pdfplumber.open(file_path) as pdf:
        for page_index, page in enumerate(pdf.pages):
            # 1. 텍스트 추출
            page_text = page.extract_text()
            if page_text:
                lines = page_text.split('\n')
                for line in lines:
                    cleaned_line = " ".join(line.strip().split())
                    if cleaned_line:
                        # 1-1. 첫 유효 텍스트가 URL인지 확인
                        if first_line:
                            first_line = False
                            if cleaned_line.startswith(('http://', 'https://')):
                                source = cleaned_line
                                continue
                            cleaned_line = re.sub(r"[^0-9A-Za-z가-힣\s.,!?\-()]", "", cleaned_line)
                            if cleaned_line:
                                full_text.append(cleaned_line)
                        else:
                            cleaned_line = re.sub(r"[^0-9A-Za-z가-힣\s.,!?\-()]", "", cleaned_line)
                            if cleaned_line:
                                full_text.append(cleaned_line)

            # 2. 이미지 처리 구조는 남겨두지만, 실제 바이너리/설명은 스킵
            if page.images:
                full_text.append("<IMAGE>")

            # 3. 페이지 구분 
            full_text.append(f"<PAGE_BREAK: {page_index}>")

    # 4. 최종 Dict 반환
    parsed_dict = {
        "doc_title": filename,
        "doc_source": source if source else filename, 
        "raw_text": " ".join(full_text),
        "chunk_list": [] 
    }
    return parsed_dict


def parse_mbox(mbox_path: str) -> list[Document]:

    # 제거할 문구들
    disclaimer_strings = [
        "본 메일은 발신전용입니다. (This is an outgoing mail only.)",
        "메일 수신을 원치 않으시면 아래의 경로에서  \"수신받지 않음\"으로 설정 바랍니다. (If you do not want to receive this type of mail, please set \"Unsubscribe\" in the path below.)",
        "경로: POVIS 전자게시 → 환경설정 → 교내회보 수신설정(Path: POVIS Bulletin Boards → Settings → Announcements Setting)"
    ]

    mbox_data = mailbox.mbox(mbox_path)
    documents = []

    for message in mbox_data:
        # 메일 제목
        subject = str(make_header(decode_header(message['Subject']))) if message['Subject'] else "No Subject"
        # 메일 날짜
        date_str = str(message['Date']) if message['Date'] else "No Date"

        # 이 메일에서 추출한 텍스트 누적
        full_text = ""

        # multipart 여부 확인
        if message.is_multipart():
            for part in message.walk():
                ctype = part.get_content_type()
                if ctype == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        text = payload.decode("utf-8", errors="ignore")
                        full_text += text
                elif ctype == "text/html":
                    payload = part.get_payload(decode=True)
                    if payload:
                        html = payload.decode("utf-8", errors="ignore")
                        soup = BeautifulSoup(html, "html.parser")
                        text = soup.get_text()
                        full_text += text
        else:
            # 단일 파트
            ctype = message.get_content_type()
            if ctype == "text/plain":
                payload = message.get_payload(decode=True)
                if payload:
                    text = payload.decode("utf-8", errors="ignore")
                    full_text = text
            elif ctype == "text/html":
                payload = message.get_payload(decode=True)
                if payload:
                    html = payload.decode("utf-8", errors="ignore")
                    soup = BeautifulSoup(html, "html.parser")
                    text = soup.get_text()
                    full_text = text

        # (2) 특정 안내문구 제거
        for disc in disclaimer_strings:
            full_text = full_text.replace(disc, "")

        # (3) 여러 줄바꿈('\n\n...') -> '\n' 하나로 축소
        full_text = re.sub(r'\n{2,}', '\n', full_text)

        # (4) 여러 공백 -> 하나의 공백으로 축소
        full_text = re.sub(r'[ \t]+', ' ', full_text)

        # (5) 앞뒤 공백 제거
        full_text = full_text.strip()

        # (6) 일시 제거
        full_text = "\n".join(full_text.split("\n")[2:])

        # 메일 본문 맨 윗부분에 Date/Title 등을 넣고 싶다면, 아래처럼 합칠 수도 있음
        # full_text = f"Date: {date_str}\nTitle: {subject}\n\n{full_text}"
        # Document 생성
        doc = Document(
            doc_type="email",
            doc_title=subject,
            doc_source=f"[교내회보메일] {subject}",  # 혹은 mbox 파일명 등 원하는 형태로
            raw_text=full_text,
        )
        documents.append(doc)

    return documents