# 목적: 대화 서비스 구현을 제공한다.
# 설명: 라우터가 호출하는 서비스 로직을 구현한다.
# 디자인 패턴: 서비스 레이어 패턴
# 참조: secondsession/api/chat/router/chat_router.py

"""대화 서비스 구현 모듈."""

from __future__ import annotations

from collections.abc import Iterable
import json
import time
import uuid
from typing import Any

from secondsession.api.chat.const import StreamEventType
from secondsession.api.chat.model import (
    ChatJobCancelResponse,
    ChatJobRequest,
    ChatJobResponse,
    ChatJobStatusResponse,
)
from secondsession.core.common.queue import ChatJobQueue, ChatStreamEventQueue
from secondsession.core.chat.graphs.chat_graph import ChatGraph


class ChatService:
    """대화 서비스 구현체."""

    def __init__(
        self,
        graph: ChatGraph,
        job_queue: ChatJobQueue,
        event_queue: ChatStreamEventQueue,
        redis_client: Any,
        poll_interval: float = 0.1,
        cancel_ttl_seconds: int | None = 1800,
    ) -> None:
        """서비스 의존성을 초기화한다.

        Args:
            graph: 대화 그래프 실행기.
            job_queue: 대화 작업 큐.
            event_queue: 스트리밍 이벤트 큐.
            redis_client: Redis 클라이언트.
            poll_interval: 스트리밍 폴링 간격(초).
            cancel_ttl_seconds: 취소 플래그 TTL(초). None이면 만료 없음.
        """
        self._graph = graph
        self._job_queue = job_queue
        self._event_queue = event_queue
        self._redis = redis_client
        self._poll_interval = poll_interval
        self._cancel_ttl_seconds = cancel_ttl_seconds

    def create_job(self, request: ChatJobRequest) -> ChatJobResponse:
        """대화 작업을 생성한다.

        구현 내용:
            - job_id/trace_id/thread_id/session_id 생성
            - 워커 큐에 작업 적재
            - 체크포인터 복구용 식별자 전달
        """
        job_id = self._build_id("job")
        trace_id = self._build_id("trace")
        thread_id = request.thread_id or self._build_id("thread")
        session_id = request.session_id or self._build_id("session")

        payload: dict[str, Any] = {
            "job_id": job_id,
            "trace_id": trace_id,
            "thread_id": thread_id,
            "session_id": session_id,
            "query": request.query,
        }
        if request.history is not None:
            payload["history"] = request.history
        if request.turn_count is not None:
            payload["turn_count"] = request.turn_count
        if request.user_id is not None:
            payload["user_id"] = request.user_id
        if request.metadata is not None:
            payload["metadata"] = request.metadata
        if request.checkpoint_id is not None:
            payload["checkpoint_id"] = request.checkpoint_id
        self._job_queue.enqueue(payload)
        self._set_status(job_id, "queued")

        return ChatJobResponse(job_id=job_id, trace_id=trace_id, thread_id=thread_id)

    def stream_events(self, job_id: str) -> Iterable[str]:
        """스트리밍 이벤트를 SSE 라인으로 반환한다.

        구현 내용:
            - Redis에서 이벤트를 소비
            - done 이벤트까지 전송
            - seq 단조 증가 유지
            - type/token/metadata/error/done 포맷 유지
        """
        last_seq = 0
        while True:
            event = self._event_queue.pop_event(job_id)
            if event is None:
                time.sleep(self._poll_interval)
                continue
            seq = self._coerce_seq(event.get("seq"))
            if seq is not None and seq <= last_seq:
                continue
            if seq is not None:
                last_seq = seq
            self._update_status_by_event(job_id, event)
            yield self._to_sse_line(event)
            if self._is_done_event(event):
                break

    def get_status(self, job_id: str) -> ChatJobStatusResponse:
        """작업 상태를 조회한다.

        구현 내용:
            - 상태 저장소 조회
            - 진행률/상태 반환
        """
        stored_status = self._get_status(job_id)
        last_event = self._event_queue.get_last_event(job_id)
        last_seq = None
        if last_event is not None:
            last_seq = self._coerce_seq(last_event.get("seq"))
        if stored_status:
            return ChatJobStatusResponse(
                job_id=job_id,
                status=stored_status,
                last_seq=last_seq,
            )
        if last_event is None:
            return ChatJobStatusResponse(job_id=job_id, status="queued", last_seq=None)
        event_type = self._normalize_event_type(last_event.get("type"))
        if event_type == StreamEventType.DONE.value:
            status = "done"
        elif event_type == StreamEventType.ERROR.value:
            status = "failed"
        else:
            status = "running"
        return ChatJobStatusResponse(job_id=job_id, status=status, last_seq=last_seq)

    def cancel(self, job_id: str) -> ChatJobCancelResponse:
        """작업을 취소한다.

        구현 내용:
            - 취소 플래그 기록
            - 워커가 취소를 확인하도록 구성
        """
        key = f"chat:cancel:{job_id}"
        if self._cancel_ttl_seconds is None:
            self._redis.set(key, "1")
        else:
            self._redis.setex(key, self._cancel_ttl_seconds, "1")
        self._set_status(job_id, "cancelled")
        return ChatJobCancelResponse(job_id=job_id, status="cancelled")

    def _build_id(self, prefix: str) -> str:
        """접두사를 포함한 식별자를 생성한다."""
        return f"{prefix}-{uuid.uuid4().hex}"

    def _to_sse_line(self, event: dict) -> str:
        """이벤트 딕셔너리를 SSE 라인으로 변환한다."""
        payload = json.dumps(event, ensure_ascii=False)
        return f"data: {payload}\n\n"

    def _coerce_seq(self, value: Any) -> int | None:
        """seq 값을 안전하게 int로 변환한다."""
        try:
            if value is None:
                return None
            return int(value)
        except (TypeError, ValueError):
            return None

    def _normalize_event_type(self, value: Any) -> str | None:
        """이벤트 타입을 문자열로 정규화한다."""
        if value is None:
            return None
        if isinstance(value, StreamEventType):
            return value.value
        return str(value)

    def _is_done_event(self, event: dict) -> bool:
        """done 이벤트 여부를 확인한다."""
        event_type = self._normalize_event_type(event.get("type"))
        return event_type == StreamEventType.DONE.value

    def _update_status_by_event(self, job_id: str, event: dict) -> None:
        """이벤트 타입에 따라 상태를 갱신한다."""
        current = self._get_status(job_id)
        if current in {"done", "failed", "cancelled"}:
            return
        event_type = self._normalize_event_type(event.get("type"))
        if event_type == StreamEventType.ERROR.value:
            self._set_status(job_id, "failed")
        elif event_type == StreamEventType.DONE.value:
            self._set_status(job_id, "done")

    def _status_key(self, job_id: str) -> str:
        """상태 저장 키를 생성한다."""
        return f"chat:status:{job_id}"

    def _set_status(self, job_id: str, status: str) -> None:
        """작업 상태를 저장한다."""
        key = self._status_key(job_id)
        self._redis.set(key, status)

    def _get_status(self, job_id: str) -> str | None:
        """작업 상태를 조회한다."""
        key = self._status_key(job_id)
        raw = self._redis.get(key)
        if raw is None:
            return None
        if isinstance(raw, bytes):
            return raw.decode("utf-8")
        return str(raw)
