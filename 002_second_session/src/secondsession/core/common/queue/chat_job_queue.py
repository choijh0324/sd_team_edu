# 목적: 대화 작업 큐를 정의한다.
# 설명: Redis 리스트 기반으로 작업을 적재/소비한다.
# 디자인 패턴: Repository, Producer-Consumer
# 참조: docs/02_backend_service_layer/04_Redis_캐시_rpush_lpop.md

"""대화 작업 큐 모듈."""

import json
import logging
from typing import Any


class ChatJobQueue:
    """대화 작업 큐."""

    def __init__(self, redis_client: Any, key: str = "chat:jobs") -> None:
        """큐를 초기화한다.

        Args:
            redis_client: Redis 클라이언트.
            key: 작업 큐 키.
        """
        self._redis = redis_client
        self._key = key

    def enqueue(self, payload: dict) -> None:
        """작업을 큐에 적재한다.

        구현 내용:
            - payload 필수 필드(job_id, trace_id, thread_id, query) 검증
            - JSON 직렬화(UTF-8, ensure_ascii=False)
            - rpush로 큐 적재 및 예외 로깅
        """
        logger = logging.getLogger(__name__)
        required_keys = {"job_id", "trace_id", "thread_id", "query"}
        missing = required_keys - payload.keys()
        if missing:
            raise ValueError(f"필수 필드 누락: {sorted(missing)}")
        try:
            serialized = json.dumps(payload, ensure_ascii=False)
        except TypeError as exc:
            logger.exception("작업 직렬화 실패: %s", exc)
            raise
        try:
            self._redis.rpush(self._key, serialized)
        except Exception as exc:  # pragma: no cover - 외부 의존성
            logger.exception("작업 큐 적재 실패: %s", exc)
            raise

    def dequeue(self) -> dict | None:
        """작업을 큐에서 꺼낸다.

        구현 내용:
            - lpop으로 큐에서 하나를 가져온다.
            - 값이 없으면 None을 반환한다.
            - JSON을 dict로 역직렬화한다.
            - 역직렬화 실패/필수 필드 누락 시 로깅 후 None 반환.
        """
        logger = logging.getLogger(__name__)
        raw = self._redis.lpop(self._key)
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.exception("작업 역직렬화 실패: %s", exc)
            return None
        required_keys = {"job_id", "trace_id", "thread_id", "query"}
        if not required_keys.issubset(data.keys()):
            logger.error("작업 필수 필드 누락: %s", data)
            return None
        return data
