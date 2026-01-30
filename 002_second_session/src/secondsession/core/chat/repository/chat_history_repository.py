# 목적: 대화 내역을 외부 저장소에 저장한다.
# 설명: Redis 리스트 기반으로 history를 적재/조회한다.
# 디자인 패턴: Repository
# 참조: docs/04_memory/05_외부_저장소_연동_전략.md

"""대화 내역 저장소 모듈."""

import json
from typing import Any


class ChatHistoryRepository:
    """Redis 기반 대화 내역 저장소."""

    def __init__(self, redis_client: Any, key_prefix: str = "chat:history") -> None:
        """저장소를 초기화한다.

        Args:
            redis_client: Redis 클라이언트.
            key_prefix: 저장 키 접두사.
        """
        self._redis = redis_client
        self._key_prefix = key_prefix

    def _build_key(self, session_id: str, thread_id: str) -> str:
        """저장 키를 생성한다."""
        return f"{self._key_prefix}:{session_id}:{thread_id}"

    def append_item(self, session_id: str, thread_id: str, item: dict) -> None:
        """대화 항목을 append-only로 저장한다."""
        payload = json.dumps(item, ensure_ascii=False)
        key = self._build_key(session_id, thread_id)
        self._redis.rpush(key, payload)

    def load_items(
        self, session_id: str, thread_id: str, start: int = 0, end: int = -1
    ) -> list[dict]:
        """대화 항목을 범위 조회한다."""
        key = self._build_key(session_id, thread_id)
        raw_items = self._redis.lrange(key, start, end)
        items: list[dict] = []
        for raw in raw_items:
            try:
                items.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
        return items
