# worker 폴더 클래스 및 함수 설명

## 목적
- 이 폴더는 동기/비동기 워커의 공통 실행 패턴을 추상화하여, 실제 워커 구현체가 일관된 방식으로 작업 큐를 소비하고 처리할 수 있도록 템플릿 메서드 패턴을 제공합니다.

---

## worker_base.py

### WorkerBase 클래스
- **역할:**
  - 동기 방식 워커의 공통 실행 흐름을 제공하는 추상 클래스입니다.
  - 작업 큐 polling, 작업 처리, 예외 처리, graceful stop 등 워커의 기본 동작을 정의합니다.
- **주요 메서드:**
  - `__init__(poll_interval: float = 0.1)`
    - 워커의 polling 간격(초)과 stop 플래그를 초기화합니다.
  - `stop()`
    - 워커의 종료를 요청합니다. (루프가 안전하게 종료됨)
  - `run_forever()`
    - 무한 루프를 돌며 `_dequeue_job()`으로 작업을 꺼내고, `_process_job()`으로 처리합니다.
    - 예외 발생 시 polling 간격을 늘려 재시도합니다.
  - `_dequeue_job()` (abstract)
    - 실제 작업 큐에서 작업을 꺼내오는 메서드(구현 필요).
    - 반환값: 작업 dict 또는 None
  - `_process_job(job: dict)` (abstract)
    - 단일 작업을 처리하는 메서드(구현 필요).
    - 인자: 작업 dict

---

## async_worker_base.py

### AsyncWorkerBase 클래스
- **역할:**
  - 비동기 방식 워커의 공통 실행 흐름을 제공하는 추상 클래스입니다.
  - asyncio 기반 polling, 작업 처리, 예외 처리, graceful stop 등 워커의 기본 동작을 정의합니다.
- **주요 메서드:**
  - `__init__(poll_interval: float = 0.1)`
    - 워커의 polling 간격(초)과 stop 플래그를 초기화합니다.
  - `stop()`
    - 워커의 종료를 요청합니다. (루프가 안전하게 종료됨)
  - `async run_forever()`
    - 무한 루프를 돌며 `await _dequeue_job()`으로 작업을 꺼내고, `await _process_job()`으로 처리합니다.
    - 예외 발생 시 polling 간격을 늘려 재시도합니다.
  - `async _dequeue_job()` (abstract)
    - 실제 작업 큐에서 작업을 비동기로 꺼내오는 메서드(구현 필요).
    - 반환값: 작업 dict 또는 None
  - `async _process_job(job: dict)` (abstract)
    - 단일 작업을 비동기로 처리하는 메서드(구현 필요).
    - 인자: 작업 dict

---

## 전체 구조 및 활용
- 실제 워커 구현체는 이 추상 클래스를 상속받아 `_dequeue_job`, `_process_job`을 구현하면 됩니다.
- 공통 루프/예외/종료 처리 로직을 재사용할 수 있어, 다양한 워커(동기/비동기) 개발이 쉬워집니다.

---

> 이 문서는 `core/common/worker` 폴더 내 각 파일의 클래스와 함수(메서드)별 역할을 3년차 이하 개발자도 이해할 수 있도록 상세히 설명한 문서입니다.
