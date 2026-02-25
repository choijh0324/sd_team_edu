# 목적: 채팅 작업 큐를 정의한다.
# 설명: 비동기 잡을 적재/소비하는 인터페이스를 제공한다.
# 디자인 패턴: Repository, Producer-Consumer
# 참조: nextStep.md

"""채팅 작업 큐 모듈."""

from collections import deque
import inspect
import json
import logging
from typing import Any


class ChatJobQueue:
    """채팅 작업 큐."""

    def __init__(self, backend: Any | None = None, key: str = "chat:jobs") -> None:
        """큐 의존성을 초기화한다.

        Args:
            backend: 큐 백엔드(예: Redis, 인메모리 큐).
            key: 작업 큐 키.
        """
        self._backend = backend
        self._key = key
        self._memory_queue: deque[str] = deque()
        self._logger = logging.getLogger(__name__)

    async def push_job(self, payload: dict[str, Any]) -> str:
        """작업을 큐에 적재한다.

        구현 내용:
            - payload 필수 필드(job_id, trace_id, thread_id, query) 검증
            - JSON 직렬화(UTF-8, ensure_ascii=False)
            - 백엔드가 있으면 rpush, 없으면 인메모리 큐에 적재
        """
        required_keys = {"job_id", "trace_id", "thread_id", "query"}
        missing = required_keys - payload.keys()
        if missing:
            raise ValueError(f"필수 필드 누락: {sorted(missing)}")

        try:
            serialized = json.dumps(payload, ensure_ascii=False)
        except TypeError as exc:
            self._logger.exception("작업 직렬화 실패: %s", exc)
            raise

        if self._backend is None:
            self._memory_queue.append(serialized)
            return str(payload["job_id"])

        try:
            await self._call_backend("rpush", self._key, serialized)
        except Exception as exc:  # pragma: no cover - 외부 의존성
            self._logger.exception("작업 큐 적재 실패: %s", exc)
            raise
        return str(payload["job_id"])

    async def pop_job(self) -> dict[str, Any] | None:
        """작업을 큐에서 꺼낸다.

        구현 내용:
            - lpop(또는 인메모리 popleft)으로 큐에서 하나를 가져온다.
            - 값이 없으면 None을 반환한다.
            - JSON을 dict로 역직렬화하고 필수 필드를 검증한다.
        """
        if self._backend is None:
            if not self._memory_queue:
                return None
            raw = self._memory_queue.popleft()
        else:
            try:
                raw = await self._call_backend("lpop", self._key)
            except Exception as exc:  # pragma: no cover - 외부 의존성
                self._logger.exception("작업 큐 소비 실패: %s", exc)
                raise

        if not raw:
            return None

        raw_text = self._decode_raw(raw)
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            self._logger.exception("작업 역직렬화 실패: %s", exc)
            return None

        required_keys = {"job_id", "trace_id", "thread_id", "query"}
        if not required_keys.issubset(data.keys()):
            self._logger.error("작업 필수 필드 누락: %s", data)
            return None
        return data

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
