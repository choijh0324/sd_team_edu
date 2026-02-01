# checkpointer 폴더 클래스 및 함수 설명

## 목적
- 이 폴더는 LangGraph 기반 대화 파이프라인에서 체크포인트(상태 저장/복구)를 위한 다양한 저장소 구현체를 제공합니다.
- 인메모리, Redis, Redis Cluster 등 다양한 환경에 맞는 체크포인터를 선택적으로 사용할 수 있습니다.

---

## inmemory_checkpointer.py

### InMemoryCheckpointer 클래스
- **역할:**
  - LangGraph의 InMemorySaver를 상속하여, 프로세스 메모리 내에서만 체크포인트를 저장/복구하는 용도의 래퍼 클래스입니다.
  - 테스트, 단일 프로세스 개발 환경 등에서 사용합니다.
- **주요 메서드:**
  - 상위 InMemorySaver의 메서드(put, get 등)를 그대로 사용합니다.

---

## redis_checkpointer.py

### build_redis_checkpointer 함수
- **역할:**
  - LangGraph의 Redis 기반 체크포인터 인스턴스를 생성하는 팩토리 함수입니다.
  - 다양한 Redis 체크포인터 클래스(RedisCheckpointSaver, RedisCheckpointer 등)를 동적으로 탐색하여 redis_url로 인스턴스를 생성합니다.
- **주요 내부 함수:**
  - `_load_class(module_name, class_name)`
    - 주어진 모듈에서 클래스 객체를 안전하게 로딩합니다.
  - `_instantiate(cls, redis_url)`
    - redis_url 인자를 다양한 방식으로 전달하여 인스턴스를 생성합니다.

---

## redis_async_checkpointer.py

### AsyncRedisClusterCheckpointSaver 클래스
- **역할:**
  - LangGraph의 BaseCheckpointSaver를 상속하여, Redis Cluster 환경에서 비동기로 체크포인트를 저장/조회/삭제하는 기능을 제공합니다.
  - 대규모 분산 환경, 고가용성 Redis Cluster에서 사용합니다.
- **주요 메서드:**
  - `__init__(redis_cluster, ttl=1440, checkpoint_ttl=1440, latest_ttl=1440)`
    - RedisCluster 클라이언트와 TTL 설정값을 받아 초기화합니다.
  - `async aput(config, checkpoint, metadata, new_versions=None)`
    - 체크포인트 데이터를 Redis에 비동기로 저장합니다.
    - pickle 직렬화, TTL 적용, 최신 체크포인트 ID 별도 저장 등
  - `async aput_writes(config, writes, task_id)`
    - 특정 태스크의 쓰기 작업 내역을 Redis에 비동기로 저장합니다.
    - checkpoint_id가 없으면 "pending"으로 저장
  - `async aget(config)`
    - config에 지정된 checkpoint_id(또는 최신) 체크포인트를 Redis에서 비동기로 조회합니다.
    - pickle 역직렬화, CheckpointTuple 반환
  - `async alist(config, before=None, limit=None, filter=None)`
    - 특정 thread_id의 모든 체크포인트를 비동기로 조회합니다.
    - before, limit, filter 조건 지원, 최신순 정렬, yield로 반환
  - `async adelete(thread_id)`
    - 특정 thread_id의 모든 체크포인트와 최신 참조를 비동기로 삭제합니다.

---

## 전체 구조 및 활용
- LangGraph 파이프라인에서 체크포인터 인스턴스를 주입하여, 상태 저장/복구/이력 관리가 가능합니다.
- 개발/테스트/운영 환경에 따라 적합한 체크포인터를 선택해 사용할 수 있습니다.

---

> 이 문서는 `core/common/checkpointer` 폴더 내 각 파일의 클래스와 함수(메서드)별 역할을 3년차 이하 개발자도 이해할 수 있도록 상세히 설명한 문서입니다.
