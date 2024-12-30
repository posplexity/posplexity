from src.rag.parse import parse_word, parse_pdf
from common.types import Document
import os



def init(db_path: str):
    # 1. file 불러오기 
    paths_list, docs_list = [], []
    for file in os.listdir(db_path):
        if file.endswith('.docx') or file.endswith('.pdf'):
            paths_list.append(os.path.join(db_path, file))

    # 2. file 파싱
    for idx, file_path in enumerate(paths_list):
        # 파일 확장자에 따라 적절한 파서 선택
        if file_path.endswith('.docx'):
            doc = Document(**parse_word(file_path))
        elif file_path.endswith('.pdf'):
            doc = Document(**parse_pdf(file_path))
            
        doc.doc_id = idx
        docs_list.append(doc)

    breakpoint()


if __name__ == "__main__":
    # upload_files(["data/test.docx"])
    init(db_path="db")