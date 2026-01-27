# secondsession

이 프로젝트는 **LangGraph + FastAPI**를 사용해
대화형 서비스 레이어를 단계적으로 구현하는 교육용 코드입니다.

## 교육 목적

- **스트리밍 응답**을 서비스 레이어에서 구성하는 방법 학습
- **대화 내역 관리/복구**를 위한 체크포인터 설계 이해
- **5턴 초과 요약** 흐름을 LangGraph로 구현
- **워커/큐 분리 구조**에서 비동기 실행 흐름 이해

---

## 구현해야 하는 과제(핵심)

아래 항목은 **학습자가 직접 구현**하도록 TODO로 남겨두었습니다.

### 1) 서비스 레이어 구현

- `src/secondsession/api/chat/service/chat_service.py`
  - `create_job`: job_id/trace_id 생성, 큐 적재
  - `stream_events`: Redis 이벤트 소비, SSE 전송, `done` 종료
  - `get_status`: 상태 조회
  - `cancel`: 취소 플래그 기록
  - 안전/폴백 이벤트 전송 규칙 정의
  - error_code/metadata 이벤트 순서 정의

### 2) 워커/큐 실행 흐름

- 워커는 **큐에서 작업을 꺼내 LangGraph 실행**
- 실행 중 **token/metadata/error/done 이벤트를 Redis에 적재**
- 스트리밍 엔드포인트는 Redis 이벤트를 소비해 전송
- 폴백 발생 시에도 done 이벤트로 정상 종료

### 3) LangGraph 노드 구현

- `src/secondsession/core/chat/nodes/answer_node.py`
  - 사용자 입력에 대한 응답 생성
  - 응답 스키마 검증 실패/타임아웃 처리
- `src/secondsession/core/chat/nodes/append_history_node.py`
  - 대화 내역 누적 (`history`, `turn_count`)
- `src/secondsession/core/chat/nodes/decide_summary_node.py`
  - 5턴 초과 시 요약 경로 결정
  - error_code 기반 폴백 분기 정책 적용
- `src/secondsession/core/chat/nodes/summary_node.py`
  - 대화 내역 요약 생성
- `src/secondsession/core/chat/nodes/safeguard_node.py`
  - 입력 안전 라벨 분류 및 error_code 설정
- `src/secondsession/core/chat/nodes/fallback_node.py`
  - 폴백 메시지 정책 적용

### 4) 체크포인터 연결

- `src/secondsession/core/common/checkpointer/redis_checkpointer.py`
  - Redis 체크포인터 생성 로직 구현
  - 메타데이터(node/route/error_code/safeguard_label) 저장 규칙
- `src/secondsession/core/chat/graphs/chat_graph.py`
  - thread_id 기반 복구 흐름 활성화
  - answer 오류 → fallback 라우팅 연결

---

## 목표 플로우

1) 대화 요청이 들어온다
2) 대화 응답을 스트리밍한다
3) 대화가 5턴을 넘어가면 요약한다
4) 그래프가 대화 내역을 계속 관리한다
5) thread_id로 대화 내역 복구가 가능해야 한다

---

## 실행 방법

### 1) uvicorn CLI 방식 (권장)

```bash
uv run uvicorn secondsession.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2) 모듈 직접 실행 방식

```bash
uv run python -m secondsession.main
```

---

## 기본 엔드포인트

- 헬스 체크: `GET /health`
- 대화 작업 생성: `POST /chat/jobs`
- 대화 스트리밍: `GET /chat/stream/{job_id}`
- 대화 상태 조회: `GET /chat/status/{job_id}`
- 대화 취소: `POST /chat/cancel/{job_id}`

---

## 주요 위치

- 애플리케이션 진입점: `src/secondsession/main.py`
- API 영역: `src/secondsession/api`
- Core 영역: `src/secondsession/core`
- 문서: `docs/`

---

## 환경 설정

프로젝트 루트에서 아래 순서로 실행하세요.

```bash
uv venv .venv
uv sync
```
