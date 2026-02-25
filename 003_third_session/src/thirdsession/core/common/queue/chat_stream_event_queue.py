# 목적: 스트리밍 이벤트 큐를 정의한다.
# 설명: 이벤트를 적재/소비하는 인터페이스를 제공한다.
# 디자인 패턴: Repository, Producer-Consumer
# 참조: nextStep.md

"""스트리밍 이벤트 큐 모듈."""

from collections import defaultdict, deque
import inspect
import json
import logging
from typing import Any


class ChatStreamEventQueue:
    """스트리밍 이벤트 큐."""

    def __init__(
        self,
        backend: Any | None = None,
        key_prefix: str = "chat:stream",
        ttl_seconds: int | None = 3600,
    ) -> None:
        """큐를 초기화한다.

        Args:
            backend: 큐 백엔드(예: Redis).
            key_prefix: job_id별 이벤트 키 접두사.
            ttl_seconds: done 이벤트 이후 리스트 보관 시간(초). None이면 만료 없음.
        """
        self._backend = backend
        self._key_prefix = key_prefix
        self._ttl_seconds = ttl_seconds
        self._memory_events: dict[str, deque[str]] = defaultdict(deque)
        self._logger = logging.getLogger(__name__)

    async def push_event(self, job_id: str, event: dict[str, Any]) -> None:
        """이벤트를 큐에 적재한다.

        구현 내용:
            - job_id별 키를 생성한다(f"{key_prefix}:{job_id}").
            - event 필수 필드(type)를 검증한다.
            - type별 필드 규칙(token/references/error/DONE)을 검증한다.
            - JSON 직렬화 후 rpush(또는 인메모리 적재)를 수행한다.
            - DONE 이벤트는 TTL 설정을 시도한다.
        """
        if not isinstance(event, dict):
            raise ValueError("event는 dict 타입이어야 합니다.")
        if "type" not in event:
            raise ValueError("event.type 필드가 필요합니다.")

        self._validate_event(event)

        key = self._key(job_id)
        try:
            serialized = json.dumps(event, ensure_ascii=False)
        except TypeError as exc:
            self._logger.exception("이벤트 직렬화 실패: %s", exc)
            raise

        if self._backend is None:
            self._memory_events[key].append(serialized)
            return

        try:
            await self._call_backend("rpush", key, serialized)
            if self._ttl_seconds is not None and self._normalize_event_type(event.get("type")) == "DONE":
                await self._call_backend("expire", key, self._ttl_seconds)
        except Exception as exc:  # pragma: no cover - 외부 의존성
            self._logger.exception("이벤트 적재 실패: %s", exc)
            raise

    async def pop_event(self, job_id: str) -> dict[str, Any] | None:
        """이벤트를 큐에서 꺼낸다.

        구현 내용:
            - job_id별 키를 생성한다.
            - lpop(또는 인메모리 popleft)으로 이벤트를 소비한다.
            - 값이 없으면 None을 반환한다.
            - JSON 역직렬화 후 dict를 반환한다.
        """
        key = self._key(job_id)

        if self._backend is None:
            if not self._memory_events[key]:
                return None
            raw = self._memory_events[key].popleft()
        else:
            try:
                raw = await self._call_backend("lpop", key)
            except Exception as exc:  # pragma: no cover - 외부 의존성
                self._logger.exception("이벤트 소비 실패: %s", exc)
                raise

        if not raw:
            return None

        raw_text = self._decode_raw(raw)
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as exc:
            self._logger.exception("이벤트 역직렬화 실패: %s", exc)
            return None

    async def get_last_seq(self, job_id: str) -> int:
        """현재 큐의 마지막 이벤트에서 index(시퀀스)를 반환한다."""
        last_event = await self.get_last_event(job_id)
        if not last_event:
            return 0
        seq = last_event.get("index")
        if isinstance(seq, int):
            return seq
        if isinstance(seq, str) and seq.isdigit():
            return int(seq)
        return 0

    async def get_last_event(self, job_id: str) -> dict[str, Any] | None:
        """현재 큐에 적재된 마지막 이벤트를 반환한다."""
        key = self._key(job_id)

        if self._backend is None:
            if not self._memory_events[key]:
                return None
            raw = self._memory_events[key][-1]
        else:
            try:
                raw = await self._call_backend("lindex", key, -1)
            except Exception as exc:  # pragma: no cover - 외부 의존성
                self._logger.exception("마지막 이벤트 조회 실패: %s", exc)
                return None

        if not raw:
            return None
        raw_text = self._decode_raw(raw)
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as exc:
            self._logger.exception("마지막 이벤트 역직렬화 실패: %s", exc)
            return None

    def _key(self, job_id: str) -> str:
        """job_id 기준 이벤트 키를 생성한다."""
        return f"{self._key_prefix}:{job_id}"

    async def _call_backend(self, method_name: str, *args: Any) -> Any:
        """백엔드 메서드를 동기/비동기 공통으로 호출한다."""
        method = getattr(self._backend, method_name)
        result = method(*args)
        if inspect.isawaitable(result):
            return await result
        return result

    def _decode_raw(self, raw: Any) -> str:
        """Redis/메모리에서 읽은 원시 값을 문자열로 변환한다."""
        if isinstance(raw, bytes):
            return raw.decode("utf-8")
        return str(raw)

    def _normalize_event_type(self, value: Any) -> str | None:
        """이벤트 타입을 문자열로 정규화한다."""
        if value is None:
            return None
        normalized = str(value)
        if normalized.lower() == "done":
            return "DONE"
        return normalized

    def _validate_event(self, event: dict[str, Any]) -> None:
        """이벤트 타입별 필수/금지 필드를 점검한다."""
        event_type = self._normalize_event_type(event.get("type"))
        status = event.get("status")
        content = event.get("content")
        items = event.get("items")

        if event_type == "token":
            if status not in {"in_progress", "end"}:
                raise ValueError("token 이벤트 status는 in_progress 또는 end여야 합니다.")
            if status == "in_progress" and content is None:
                raise ValueError("token(in_progress) 이벤트는 content가 필요합니다.")
            if items is not None:
                raise ValueError("token 이벤트에서는 items를 사용할 수 없습니다.")
            return

        if event_type == "references":
            if status != "end":
                raise ValueError("references 이벤트 status는 end여야 합니다.")
            if not isinstance(items, list):
                raise ValueError("references 이벤트는 items(list)가 필요합니다.")
            if content is not None:
                raise ValueError("references 이벤트에서는 content를 사용할 수 없습니다.")
            return

        if event_type == "error":
            if content is None or str(content).strip() == "":
                raise ValueError("error 이벤트는 content가 필요합니다.")
            if status is not None and status != "end":
                raise ValueError("error 이벤트 status는 end만 허용됩니다.")
            return

        if event_type == "DONE":
            forbidden = ("status", "content", "index", "items")
            for key in forbidden:
                if event.get(key) is not None:
                    raise ValueError("DONE 이벤트는 type 외 필드를 가질 수 없습니다.")
            return

        raise ValueError(f"지원하지 않는 이벤트 타입입니다: {event_type}")
