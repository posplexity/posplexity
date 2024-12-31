# Posplexity

## 소개
Posplexity는 문서 기반 질의응답 시스템으로, 다양한 문서 형식을 지원하고 효율적인 검색과 응답 생성을 제공하는 프로젝트입니다.

## 주요 기능
- 다양한 문서 형식 지원 및 파싱
- 벡터 데이터베이스를 활용한 효율적인 검색
- GPT 및 Deepseek 등 다양한 LLM 모델 지원
- Streamlit 기반의 사용자 인터페이스

## 프로젝트 구조
```
posplexity/
├── src/
│   ├── llm/              # LLM 관련 모듈
│   │   ├── deepseek/     # Deepseek 모델 구현
│   │   └── gpt/          # GPT 모델 구현
│   ├── rag/              # RAG(Retrieval-Augmented Generation) 관련 모듈
│   │   ├── chunk.py      # 문서 청킹
│   │   ├── embedding.py  # 임베딩 생성
│   │   └── parse.py      # 문서 파싱
│   ├── search/           # 검색 관련 모듈
│   └── utils/            # 유틸리티 함수
├── common/               # 공통 모듈
│   ├── config.py        # 설정 관리
│   ├── globals.py       # 전역 변수
│   └── types.py         # 타입 정의
├── streamlit_app.py     # Streamlit 웹 애플리케이션
└── upload.py            # 파일 업로드 처리
```

## 설치 방법
1. Python 3.11 이상 설치
2. Poetry를 사용한 의존성 설치:
```bash
poetry install
```

## 환경 설정
1. `.env` 파일 생성 및 필요한 환경 변수 설정:
```
OPENAI_API_KEY=your_api_key
```

## 실행 방법
Streamlit 애플리케이션 실행:
```bash
poetry run streamlit run streamlit_app.py
```

## 주요 컴포넌트
### RAG (Retrieval-Augmented Generation)
- `chunk.py`: 문서를 적절한 크기로 분할
- `embedding.py`: 문서 청크의 벡터 임베딩 생성
- `parse.py`: 다양한 문서 형식 파싱

### LLM (Large Language Models)
- GPT 모델 지원
- Deepseek 모델 지원
- 커스텀 프롬프트 템플릿 (`src/llm/deepseek/prompt/`)

### 검색
- Qdrant 벡터 데이터베이스 활용
- 시맨틱 검색 구현

## 라이선스
MIT License
