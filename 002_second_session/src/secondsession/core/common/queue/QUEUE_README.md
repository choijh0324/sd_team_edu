# core/common/queue 모듈 상세 설명

## 목적
- 이 디렉토리는 대화 서비스의 작업(Job)과 스트리밍 이벤트(Event)를 Redis 기반 큐로 관리하는 핵심 모듈을 제공합니다.
- Producer-Consumer 패턴을 적용하여, 비동기 작업 분배와 실시간 이벤트 처리를 담당합니다.

---

## chat_job_queue.py

### ChatJobQueue 클래스
- **역할:** 대화 작업(Job)을 Redis 리스트에 적재(rpush)하고, 워커가 소비(lpop)할 수 있도록 관리합니다.

#### 주요 메서드
- `__init__(redis_client, key="chat:jobs")`
  - Redis 클라이언트와 큐 키를 주입받아 큐를 초기화합니다.
- `enqueue(payload: dict)`
  - 작업을 큐에 적재합니다.
  - 필수 필드(job_id, trace_id, thread_id, query) 검증 후 JSON 직렬화하여 rpush로 저장합니다.
  - 직렬화/적재 실패 시 예외 및 로깅 처리합니다.
- `dequeue() -> dict | None`
  - 큐에서 작업을 하나 꺼냅니다(lpop).
  - 값이 없으면 None 반환, JSON 역직렬화 및 필수 필드 검증 후 dict 반환.
  - 역직렬화 실패/필수 필드 누락 시 로깅 후 None 반환.

---

## chat_stream_event_queue.py

### ChatStreamEventQueue 클래스
- **역할:** 대화 스트리밍 과정에서 발생하는 이벤트(토큰, 메타데이터, 에러, 완료 등)를 Redis 리스트에 적재/소비합니다.

#### 주요 메서드
- `__init__(redis_client, key_prefix="chat:stream", ttl_seconds=3600)`
  - Redis 클라이언트, 키 프리픽스, TTL(보관 시간)을 주입받아 큐를 초기화합니다.
- `push_event(job_id: str, event: dict)`
  - job_id별로 이벤트를 큐에 적재합니다(rpush).
  - 필수 필드(type, trace_id, seq) 및 이벤트 타입별 추가 필드 검증 후 JSON 직렬화하여 저장합니다.
  - done 이벤트일 경우 TTL을 설정합니다.
- `pop_event(job_id: str) -> dict | None`
  - job_id별 큐에서 이벤트를 하나 꺼냅니다(lpop).
  - 값이 없으면 None 반환, JSON 역직렬화 후 dict 반환.
  - 역직렬화 실패 시 로깅 후 None 반환.
- `get_last_seq(job_id: str) -> int`
  - 해당 job_id 큐의 마지막 이벤트의 seq 값을 반환합니다.
  - 값이 없거나 역직렬화 실패 시 0 반환.
- `get_last_event(job_id: str) -> dict | None`
  - 해당 job_id 큐의 마지막 이벤트를 반환합니다.
  - 값이 없거나 역직렬화 실패 시 None 반환.
- `_validate_event(event: dict)`
  - 이벤트 타입별로 필수 필드가 있는지 검증합니다.
  - 예: token 이벤트는 content 필요, metadata 이벤트는 metadata 필요 등.
- `_normalize_event_type(value: Any) -> str | None`
  - 이벤트 타입을 문자열로 정규화합니다.

---

## 전체 구조 및 동작 요약
- **Job 등록:** ChatJobQueue에 작업 적재 → 백엔드 워커가 작업을 소비
- **이벤트 스트리밍:** ChatStreamEventQueue에 처리 결과/토큰/에러 등 이벤트 적재 → API에서 실시간 소비 및 스트리밍 응답
- **Redis를 활용한 분산 큐:** 여러 워커/프로세스가 동시에 작업을 분배/처리할 수 있도록 설계

---

## 참고
- 자세한 구현 및 사용 예시는 각 서비스 레이어(chat_service.py 등)와 워커 코드에서 확인할 수 있습니다.
- Redis 리스트(rpush/lpop) 기반으로, 확장성과 실시간성이 뛰어난 구조입니다.

---

> 이 문서는 `core/common/queue` 폴더 내 주요 파일의 클래스와 각 메서드의 역할을 3년차 이하 개발자도 이해할 수 있도록 상세히 설명한 문서입니다.
