# thirdsession

이 프로젝트는 LangChain/LangGraph 입문자를 대상으로 한 **실전형 교육 코스**입니다.  
"RAG는 검색과 생성의 조합"이라는 관점을 중심으로, 검색 전략부터 그래프 기반 파이프라인까지 단계적으로 학습합니다.

## 교육 방향성

- **한 작업-한 책임** 원칙으로 단계를 분리한다.
- 검색 결과는 **정책 필터 → 정규화 → 병합 → 후처리**로 안정화한다.
- LangGraph를 사용해 **태스크 분리와 흐름 제어**를 구현한다.
- 실패 응답은 **폴백/재시도 전략**으로 복구한다.

## 학습 콘텐츠

- 교재 문서: `docs/`
- 코드 템플릿: `src/thirdsession/`
- RAG 엔드포인트: `/rag_chat`

## 사전 준비

- Postgres 설치 및 구동
- PGVector 확장 설치 및 활성화
  - DB에서 `CREATE EXTENSION vector;` 실행

### Ubuntu 기준 설치 가이드(요약)

아래 명령은 **Ubuntu 환경 기준**입니다. 로컬 환경/버전에 맞게 조정하세요.

```bash
# 1) PostgreSQL 설치 및 서비스 시작
sudo apt update
sudo apt install -y postgresql postgresql-contrib
sudo systemctl enable --now postgresql

# 2) PostgreSQL 버전 확인
psql --version

# 3) PGVector 설치(버전에 맞는 패키지 선택)
# 예: PostgreSQL 16 → postgresql-16-pgvector
sudo apt install -y postgresql-16-pgvector

# 4) DB 접속 후 확장 활성화
sudo -u postgres psql
CREATE EXTENSION vector;
```

## 구현해야 하는 과제

아래 항목은 코드의 `TODO`/`NotImplementedError`를 기준으로 정리했습니다.  
학습자는 각 항목을 직접 구현해 전체 RAG 파이프라인을 완성합니다.

### 1) API/서비스 레이어 구현

- `src/thirdsession/main.py`
  - 앱 생성 시 의존성 주입 구성
  - 라우터 등록 방식 확정
- `src/thirdsession/api/chat/router/rag_chat_router.py`
  - `/rag_chat` 요청 처리 로직 구현
  - `/rag_chat/stream` 스트리밍 응답 구현
- `src/thirdsession/api/chat/service/rag_chat_service.py`
  - 요청 → 유스케이스 호출 → 응답 변환
  - 예외 처리/로깅/메트릭 수집
- `src/thirdsession/api/chat/model/rag_chat_request.py`
  - 입력 필드 확장 및 검증 규칙 정의
- `src/thirdsession/api/chat/model/rag_chat_response.py`
  - 응답 포맷(요약/상세/메타) 확장

### 2) 유스케이스/파이프라인 구성

- `src/thirdsession/core/chat/usecases/rag_chat_usecase.py`
  - RAG 파이프라인 구성 및 실행
  - 리트리버/벡터 스토어 주입 구조 확장
  - 프롬프트/후처리/생성 단계 분리

### 3) 검색/벡터 검색 구성 요소

- `src/thirdsession/core/retrieval/document_model.py`
  - 문서 유효성 검증 규칙 정의
- `src/thirdsession/core/retrieval/chunker.py`
  - 청크 분할 기준/오버랩 규칙 구현
- `src/thirdsession/core/retrieval/embedding_service.py`
  - 임베딩 API 호출 및 배치 처리 구현
- `src/thirdsession/core/retrieval/vector_repository.py`
  - 저장/검색 쿼리 및 필터 구현
- `src/thirdsession/core/retrieval/search_service.py`
  - 점수 임계값/중복 제거/정렬 규칙 구현
- `src/thirdsession/core/retrieval/score_normalizer.py`
  - 거리 → 유사도 변환 및 정규화 구현
- `src/thirdsession/core/retrieval/metadata_filter.py`
  - 권한/언어/버전 필터 규칙 구현
- `src/thirdsession/core/retrieval/filter_expression_builder.py`
  - 필수/선택 조건 분리 및 표현식 구성
- `src/thirdsession/core/retrieval/metadata_schema_repository.py`
  - 메타데이터 키/값 조회 로직 구현
- `src/thirdsession/core/retrieval/hybrid_fusion.py`
  - 가중합/RRF/재정렬 결합 방식 구현

### 4) 검색 전략 그래프 구성

- `src/thirdsession/core/chat/graphs/query_decompose_graph.py`
  - 쿼리 분해 → 병렬 검색 → 병합 그래프 구성
- `src/thirdsession/core/chat/graphs/search_verify_merge_graph.py`
  - 검색 → 검증 → 병합 그래프 구성
- `src/thirdsession/core/chat/graphs/adaptive_hyde_graph.py`
  - 적응형 HyDE 그래프 구성
- `src/thirdsession/core/chat/graphs/rag_pipeline_graph.py`
  - 서비스 수준 전체 파이프라인 그래프 구성

### 5) LangGraph 노드 구현

- `src/thirdsession/core/chat/nodes/query_decompose_node.py`
  - 질문 분해 LLM 호출 및 파싱
- `src/thirdsession/core/chat/nodes/search_node.py`
  - 리트리버 호출 및 예외 처리
- `src/thirdsession/core/chat/nodes/async_search_node.py`
  - 비동기 병렬 검색 및 동시성 제한
- `src/thirdsession/core/chat/nodes/verify_node.py`
  - 검색 결과 검증 로직
- `src/thirdsession/core/chat/nodes/hyde_node.py`
  - HyDE 생성 및 재검색 로직
- `src/thirdsession/core/chat/nodes/merge_node.py`
  - 병합/정규화/중복 제거 규칙
- `src/thirdsession/core/chat/nodes/postprocess_node.py`
  - 후처리 파이프라인 호출
- `src/thirdsession/core/chat/nodes/generate_node.py`
  - 답변 생성 및 출력 포맷 규칙
- `src/thirdsession/core/chat/nodes/stream_answer_node.py`
  - 답변 스트리밍 규칙
- `src/thirdsession/core/chat/nodes/stream_sources_node.py`
  - 근거 스트리밍 규칙

### 6) 프롬프트 구성

- `src/thirdsession/core/chat/prompts/query_decompose_prompt.py`
  - 쿼리 분해 프롬프트 정의
- `src/thirdsession/core/chat/prompts/verify_prompt.py`
  - 검색 검증 프롬프트 정의
- `src/thirdsession/core/chat/prompts/hyde_prompt.py`
  - HyDE 프롬프트 정의
- `src/thirdsession/core/chat/prompts/answer_prompt.py`
  - 답변 생성 프롬프트 정의

### 7) 후처리 구성(LLM 기반)

- `src/thirdsession/core/postprocessing/postprocess_pipeline.py`
  - 정책 필터/중복 제거/다양성/재정렬/압축 구현
- `src/thirdsession/core/postprocessing/llm_reranker.py`
  - LLM 재정렬기 구현

---

## 목표 플로우

1) 검색 전략 선택/실행  
2) 정책 기반 필터 적용  
3) 점수 정규화 및 결과 병합  
4) 후처리(중복 제거/다양성/재정렬/압축)  
5) 근거 기반 답변 생성  
6) 스트리밍 응답(답변 → 근거)  

## 실행 방법

```bash
uv run uvicorn thirdsession.main:app --host 0.0.0.0 --port 8000 --reload
```

또는

```bash
uv run python -m thirdsession.main
```

## 기본 엔드포인트

- 헬스 체크: `GET /health`
- RAG 요청: `POST /rag_chat`
- RAG 스트리밍: `POST /rag_chat/stream`

## 주요 위치

- 애플리케이션 진입점: `src/thirdsession/main.py`
- API 영역: `src/thirdsession/api`
- Core 영역: `src/thirdsession/core`

## 환경 설정

프로젝트 루트에서 아래 순서로 실행하세요.

```txt
uv venv .venv
uv sync
```
