# 목적: 스트림 이벤트 큐를 정의한다.
# 설명: 작업별 스트림 이벤트를 Redis 리스트로 관리한다.
# 디자인 패턴: 큐 패턴
# 참조: fourthsession/core/common/queue/redis_connection_provider.py

"""스트림 이벤트 큐 모듈."""

from __future__ import annotations

import json

from fourthsession.core.common.queue.redis_connection_provider import (
    RedisConnectionProvider,
)


class RedisStreamEventQueue:
    """Redis 기반 스트림 이벤트 큐."""

    def __init__(
        self,
        connection_provider: RedisConnectionProvider | None = None,
        key_prefix: str = "housing:stream",
    ) -> None:
        """스트림 이벤트 큐를 초기화한다."""
        self._connection_provider = connection_provider or RedisConnectionProvider()
        self._client = self._connection_provider.get_client()
        self._key_prefix = key_prefix

    def _build_key(self, job_id: str) -> str:
        """작업 식별자 기반 Redis 키를 생성한다."""
        return f"{self._key_prefix}:{job_id}"

    def push_event(self, job_id: str, event: dict) -> int:
        """스트림 이벤트를 적재한다.

        Args:
            job_id (str): 작업 식별자.
            event (dict): 이벤트 데이터.

        Returns:
            int: 스트림 큐 길이.
        """
        stream_key = self._build_key(job_id)
        serialized_event = json.dumps(event, ensure_ascii=False)
        queue_length = self._client.rpush(stream_key, serialized_event)
        return int(queue_length)

    def pop_event(self, job_id: str) -> dict | None:
        """스트림 이벤트를 가져온다.

        Args:
            job_id (str): 작업 식별자.

        Returns:
            dict | None: 이벤트 데이터.
        """
        stream_key = self._build_key(job_id)
        raw_event = self._client.lpop(stream_key)
        if raw_event is None:
            return None
        return dict(json.loads(raw_event))
