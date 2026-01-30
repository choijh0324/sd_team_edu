# 목적: 스트리밍 이벤트 큐를 정의한다.
# 설명: Redis 리스트 기반으로 이벤트를 적재/소비한다.
# 디자인 패턴: Repository, Producer-Consumer
# 참조: docs/02_backend_service_layer/04_Redis_캐시_rpush_lpop.md

"""스트리밍 이벤트 큐 모듈."""

import json
import logging
from typing import Any


class ChatStreamEventQueue:
    """스트리밍 이벤트 큐."""

    def __init__(self, redis_client: Any, key_prefix: str = "chat:stream") -> None:
        """큐를 초기화한다.

        Args:
            redis_client: Redis 클라이언트.
            key_prefix: job_id별 이벤트 키 접두사.
        """
        self._redis = redis_client
        self._key_prefix = key_prefix

    async def push_event(self, job_id: str, event: dict) -> None:
        """이벤트를 큐에 적재한다.

        TODO:
            - job_id별 키를 생성한다(f\"{key_prefix}:{job_id}\").
            - event 필수 필드(type, trace_id, seq)를 검증한다.
            - event를 JSON 문자열로 직렬화한다(UTF-8, ensure_ascii=False).
            - rpush로 이벤트를 적재한다.
            - seq 단조 증가 규칙을 보장한다(워커 측에서 증가).
        """
        logger = logging.getLogger(__name__)
        required_keys = {"type", "trace_id", "seq"}
        missing = required_keys - event.keys()
        if missing:
            raise ValueError(f"필수 필드 누락: {sorted(missing)}")
        key = f"{self._key_prefix}:{job_id}"
        try:
            serialized = json.dumps(event, ensure_ascii=False)
        except TypeError as exc:
            logger.exception("이벤트 직렬화 실패: %s", exc)
            raise
        try:
            self._redis.rpush(key, serialized)
        except Exception as exc:  # pragma: no cover - 외부 의존성
            logger.exception("이벤트 적재 실패: %s", exc)
            raise

    async def pop_event(self, job_id: str) -> dict | None:
        """이벤트를 큐에서 꺼낸다.

        TODO:
            - job_id별 키를 생성한다.
            - lpop으로 이벤트를 소비한다.
            - 값이 없으면 None을 반환한다.
            - JSON을 dict로 역직렬화한다.
            - 역직렬화 실패 시 스킵/로깅 규칙을 정의한다.
        """
        logger = logging.getLogger(__name__)
        key = f"{self._key_prefix}:{job_id}"
        raw = self._redis.lpop(key)
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.exception("이벤트 역직렬화 실패: %s", exc)
            return None
        return data

    def get_last_seq(self, job_id: str) -> int:
        """현재 큐에 적재된 마지막 seq를 반환한다."""
        logger = logging.getLogger(__name__)
        key = f"{self._key_prefix}:{job_id}"
        raw = self._redis.lindex(key, -1)
        if not raw:
            return 0
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.exception("마지막 이벤트 역직렬화 실패: %s", exc)
            return 0
        seq = data.get("seq")
        return int(seq) if isinstance(seq, int | float | str) else 0
