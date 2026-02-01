# ChatService 작동 원리 및 구조 설명

## 목적
- `ChatService`는 대화형 API의 핵심 서비스 레이어로, 대화 작업(Job) 생성, 상태 관리, 스트리밍 응답, 취소 등 주요 비즈니스 로직을 담당합니다.
- FastAPI 라우터에서 직접 호출되어, 외부 요청과 백엔드 처리(그래프, 큐, Redis 등)를 연결합니다.

---

## 주요 메서드 및 동작 흐름

### 1. 생성자 (`__init__`)
- **의존성 주입:**
  - `graph`: 대화 처리 파이프라인(LangGraph 기반)
  - `job_queue`: 작업 등록용 Redis 큐
  - `event_queue`: 스트리밍 이벤트용 Redis 큐
  - `redis_client`: 상태/취소 관리용 Redis 클라이언트
  - `poll_interval`: 스트리밍 폴링 주기(초)
  - `cancel_ttl_seconds`: 취소 플래그 TTL(초)

---

### 2. create_job(request: ChatJobRequest) → ChatJobResponse
- **역할:**
  - 새로운 대화 작업을 등록합니다.
- **주요 동작:**
  1. job_id, trace_id, thread_id, session_id 등 식별자 생성
  2. 요청 payload를 Redis 작업 큐에 적재
  3. 상태를 "queued"로 저장
  4. job_id, trace_id, thread_id 반환

---

### 3. stream_events(job_id: str) → Iterable[str]
- **역할:**
  - SSE(Server-Sent Events) 방식으로 실시간 스트리밍 응답을 제공합니다.
- **주요 동작:**
  1. Redis 이벤트 큐에서 job_id별 이벤트 polling
  2. 이벤트를 SSE 포맷(`data: ...\n\n`)으로 변환하여 yield
  3. "done" 이벤트가 오면 스트림 종료
  4. 이벤트별로 상태 갱신

---

### 4. get_status(job_id: str) → ChatJobStatusResponse
- **역할:**
  - 작업의 현재 상태(queued, running, done, failed 등)와 마지막 이벤트 seq를 반환합니다.
- **주요 동작:**
  1. Redis에서 상태 및 마지막 이벤트 조회
  2. 상태/seq를 ChatJobStatusResponse로 반환

---

### 5. cancel(job_id: str) → ChatJobCancelResponse
- **역할:**
  - 작업 취소 요청을 처리합니다.
- **주요 동작:**
  1. Redis에 취소 플래그 기록(워커가 확인)
  2. 상태를 "cancelled"로 변경
  3. 취소 응답 반환

---

## 내부 유틸리티 메서드
- **_build_id(prefix):** UUID 기반 식별자 생성
- **_to_sse_line(event):** 이벤트를 SSE 라인으로 변환
- **_coerce_seq(value):** seq 값을 안전하게 int로 변환
- **_normalize_event_type(value):** 이벤트 타입 정규화
- **_is_done_event(event):** done 이벤트 여부 확인
- **_update_status_by_event(job_id, event):** 이벤트에 따라 상태 갱신
- **_set_status/_get_status:** Redis에 상태 저장/조회

---

## 전체 처리 흐름 요약
1. **Job 등록:** create_job → Redis 작업 큐 적재
2. **백엔드 워커:** 작업 큐에서 job 소비 → 그래프 실행 → 이벤트 큐에 결과 push
3. **클라이언트:** stream_events로 실시간 스트리밍 응답 수신
4. **상태/취소:** get_status, cancel 등으로 관리

---

## 참고
- 서비스 레이어 패턴 적용: 라우터와 백엔드 처리(그래프, 큐, Redis 등) 사이의 비즈니스 로직을 분리
- Redis를 통한 비동기 작업 분배 및 실시간 이벤트 스트리밍 구조
- LangGraph 기반 대화 파이프라인과 연동

---

> 이 문서는 `src/secondsession/api/chat/service/chat_service.py`의 구조와 작동 원리를 3년차 이하 개발자도 이해할 수 있도록 요약한 문서입니다.
