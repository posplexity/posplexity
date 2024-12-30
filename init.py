from src.rag.parse import parse_word
from common.types import Document
import os



def init(db_path: str):
    # 1. file 불러오기
    paths_list, docs_list = [], []
    for file in os.listdir(db_path):
        if file.endswith('.docx'):
            paths_list.append(os.path.join(db_path, file))

    # 2. file 파싱
    for idx, file_path in enumerate(paths_list):
        doc = Document(**parse_word(file_path))
        doc.doc_id = idx
        docs_list.append(doc)

    breakpoint()


if __name__ == "__main__":
    # upload_files(["data/test.docx"])
    init(db_path="db")