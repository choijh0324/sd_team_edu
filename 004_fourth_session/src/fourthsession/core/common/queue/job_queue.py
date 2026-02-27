# 목적: Redis 기반 작업 큐를 정의한다.
# 설명: 작업 요청을 리스트에 적재하고 소비한다.
# 디자인 패턴: 큐 패턴
# 참조: fourthsession/core/common/queue/redis_connection_provider.py

"""작업 큐 모듈."""

from __future__ import annotations

import json

from fourthsession.core.common.queue.redis_connection_provider import (
    RedisConnectionProvider,
)


class RedisJobQueue:
    """Redis 작업 큐."""

    def __init__(
        self,
        connection_provider: RedisConnectionProvider | None = None,
        queue_key: str = "housing:jobs",
    ) -> None:
        """작업 큐를 초기화한다."""
        self._connection_provider = connection_provider or RedisConnectionProvider()
        self._client = self._connection_provider.get_client()
        self._queue_key = queue_key

    def enqueue(self, payload: dict) -> int:
        """작업을 큐에 적재한다.

        Args:
            payload (dict): 작업 페이로드.

        Returns:
            int: 큐 길이.
        """
        serialized_payload = json.dumps(payload, ensure_ascii=False)
        queue_length = self._client.rpush(self._queue_key, serialized_payload)
        return int(queue_length)

    def dequeue(self) -> dict | None:
        """작업을 큐에서 가져온다.

        Returns:
            dict | None: 작업 페이로드.
        """
        raw_payload = self._client.lpop(self._queue_key)
        if raw_payload is None:
            return None
        return dict(json.loads(raw_payload))
