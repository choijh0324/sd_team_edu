# 목적: 대화 워커 실행 흐름을 정의한다.
# 설명: 큐 소비 → 그래프 실행 → 스트리밍 이벤트 적재를 담당한다.
# 디자인 패턴: Worker, Producer-Consumer
# 참조: docs/02_backend_service_layer/05_비동기_엔드포인트_분리_전략.md

"""대화 워커 모듈."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Any

from secondsession.core.chat.graphs import build_chat_graph
from secondsession.core.chat.const.error_code import ErrorCode
from secondsession.api.chat.const.stream_event_type import StreamEventType
from secondsession.api.chat.const.metadata_event_type import MetadataEventType
from secondsession.core.common.queue import ChatJobQueue, ChatStreamEventQueue
from secondsession.core.common.checkpointer import (
    InMemoryCheckpointer,
    build_redis_checkpointer,
)


class ChatWorker:
    """대화 워커."""

    def __init__(
        self,
        job_queue: ChatJobQueue,
        event_queue: ChatStreamEventQueue,
        checkpointer: Any | None,
        poll_interval: float = 0.1,
    ) -> None:
        """워커를 초기화한다.

        Args:
            job_queue: 대화 작업 큐.
            event_queue: 스트리밍 이벤트 큐.
            checkpointer: LangGraph 체크포인터.
            poll_interval: 큐 폴링 간격(초).
        """
        self._job_queue = job_queue
        self._event_queue = event_queue
        self._checkpointer = checkpointer or self._build_checkpointer()
        self._poll_interval = poll_interval

    def _build_checkpointer(self) -> Any:
        """환경 변수 기반으로 체크포인터를 생성한다."""
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            return build_redis_checkpointer(redis_url)
        return InMemoryCheckpointer()

    def run_forever(self) -> None:
        """워커를 루프 형태로 실행한다.

        TODO:
            - 큐에서 작업을 가져와 처리한다.
            - 작업이 없으면 poll_interval 만큼 대기한다.
            - 종료/취소 정책을 정의한다(취소 키 확인).
        """
        while True:
            job = self._job_queue.dequeue()
            if job is None:
                time.sleep(self._poll_interval)
                continue
            self._process_job(job)

    def _process_job(self, job: dict) -> None:
        """단일 작업을 처리한다.

        TODO:
            - 그래프를 빌드하고 invoke/stream을 실행한다.
            - config에 thread_id를 넣어 체크포인터 복구를 활성화한다.
            - 실행 중 token/metadata/error 이벤트를 event_queue에 적재한다.
            - 메타데이터 content는 JSON 문자열(예: event, message, route, timestamp)을 사용한다.
            - error 발생 시 error → done 순서로 적재한다.
            - done 이벤트를 반드시 적재하고 종료한다.
        """
        graph = build_chat_graph(self._checkpointer)
        seq = self._event_queue.get_last_seq(job_id)
        trace_id = job.get("trace_id", "unknown")
        job_id = job.get("job_id", "unknown")
        cancel_key = f"chat:cancel:{job_id}"
        if self._job_queue._redis.get(cancel_key):
            seq += 1
            self._event_queue.push_event(job_id, {
                "type": StreamEventType.METADATA.value,
                "content": json.dumps({
                    "event": MetadataEventType.JOB_ERROR.value,
                    "message": ErrorCode.CANCELLED.user_message,
                    "timestamp": datetime.utcnow().isoformat(),
                    "node": "worker",
                    "route": None,
                    "error_code": ErrorCode.CANCELLED,
                    "safeguard_label": None,
                }, ensure_ascii=False),
                "node": "worker",
                "trace_id": trace_id,
                "seq": seq,
            })
            seq += 1
            self._event_queue.push_event(job_id, {
                "type": StreamEventType.ERROR.value,
                "content": ErrorCode.CANCELLED.user_message,
                "node": "worker",
                "route": None,
                "error_code": ErrorCode.CANCELLED,
                "safeguard_label": None,
                "trace_id": trace_id,
                "seq": seq,
            })
            seq += 1
            self._event_queue.push_event(job_id, {
                "type": StreamEventType.DONE.value,
                "content": None,
                "node": None,
                "route": None,
                "trace_id": trace_id,
                "seq": seq,
            })
            return

        seq += 1
        self._event_queue.push_event(job_id, {
            "type": StreamEventType.METADATA.value,
            "content": json.dumps({
                "event": MetadataEventType.JOB_START.value,
                "message": "워커 실행 시작",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "node": "worker",
                "route": None,
                "error_code": None,
                "safeguard_label": None,
            }, ensure_ascii=False),
            "node": "worker",
            "trace_id": trace_id,
            "seq": seq,
        })

        state = {
            "history": job.get("history", []),
            "summary": None,
            "turn_count": job.get("turn_count", 0) or 0,
            "last_user_message": job.get("query", ""),
            "last_assistant_message": None,
            "safeguard_label": None,
            "route": None,
            "error_code": None,
            "trace_id": trace_id,
            "thread_id": thread_id,
            "user_id": job.get("user_id"),
        }

        seq += 1
        self._event_queue.push_event(job_id, {
            "type": StreamEventType.METADATA.value,
            "content": json.dumps({
                "event": MetadataEventType.NODE_START.value,
                "message": "그래프 실행 시작",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "node": "graph",
                "route": None,
                "error_code": None,
                "safeguard_label": None,
            }, ensure_ascii=False),
            "node": "graph",
            "trace_id": trace_id,
            "seq": seq,
        })
        thread_id = job.get("thread_id") or f"thread-{trace_id}"
        configurable = {"thread_id": thread_id}
        checkpoint_id = job.get("checkpoint_id")
        if checkpoint_id:
            configurable["checkpoint_id"] = checkpoint_id
        result = graph.invoke(state, config={"configurable": configurable})
        seq += 1
        self._event_queue.push_event(job_id, {
            "type": StreamEventType.METADATA.value,
            "content": json.dumps({
                "event": MetadataEventType.NODE_END.value,
                "message": "그래프 실행 종료",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "node": "graph",
                "route": None,
                "error_code": None,
                "safeguard_label": None,
            }, ensure_ascii=False),
            "node": "graph",
            "trace_id": trace_id,
            "seq": seq,
        })

        error_code = result.get("error_code")
        safeguard_label = result.get("safeguard_label")
        last_message = result.get("last_assistant_message", "")
        route = result.get("route")
        user_message = result.get("user_message")
        self._save_checkpoint(
            thread_id=thread_id,
            state=result,
            metadata={
                "node": "graph_end",
                "route": route,
                "error_code": error_code,
                "safeguard_label": safeguard_label,
            },
        )

        if route or error_code or safeguard_label:
            seq += 1
            metadata_payload = {
                "event": (
                    MetadataEventType.FALLBACK.value
                    if error_code
                    else MetadataEventType.ROUTE_DECISION.value
                ),
                "message": user_message or "",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "node": "transition",
                "route": route,
                "error_code": error_code,
                "safeguard_label": safeguard_label,
            }
            self._event_queue.push_event(job_id, {
                "type": StreamEventType.METADATA.value,
                "content": json.dumps(metadata_payload, ensure_ascii=False),
                "node": "transition",
                "route": route,
                "error_code": error_code,
                "safeguard_label": safeguard_label,
                "trace_id": trace_id,
                "seq": seq,
            })

        if error_code:
            seq += 1
            self._event_queue.push_event(job_id, {
                "type": StreamEventType.ERROR.value,
                "content": error_code.user_message,
                "node": "answer",
                "route": route,
                "error_code": error_code,
                "safeguard_label": safeguard_label,
                "trace_id": trace_id,
                "seq": seq,
            })
            seq += 1
            self._event_queue.push_event(job_id, {
                "type": StreamEventType.DONE.value,
                "content": None,
                "node": None,
                "route": route,
                "trace_id": trace_id,
                "seq": seq,
            })
            seq += 1
            self._event_queue.push_event(job_id, {
                "type": StreamEventType.METADATA.value,
                "content": json.dumps({
                    "event": MetadataEventType.JOB_END.value,
                    "message": "워커 실행 종료",
                    "timestamp": datetime.utcnow().isoformat(),
                    "node": "worker",
                    "route": route,
                    "error_code": error_code,
                    "safeguard_label": safeguard_label,
                }, ensure_ascii=False),
                "node": "worker",
                "trace_id": trace_id,
                "seq": seq,
            })
            return

        if last_message:
            seq += 1
            self._event_queue.push_event(job_id, {
                "type": StreamEventType.TOKEN.value,
                "content": last_message,
                "node": "answer",
                "route": route,
                "trace_id": trace_id,
                "seq": seq,
            })

        seq += 1
        self._event_queue.push_event(job_id, {
            "type": StreamEventType.DONE.value,
            "content": None,
            "node": None,
            "route": route,
            "trace_id": trace_id,
            "seq": seq,
        })
        seq += 1
        self._event_queue.push_event(job_id, {
            "type": StreamEventType.METADATA.value,
            "content": json.dumps({
                "event": MetadataEventType.JOB_END.value,
                "message": "워커 실행 종료",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "node": "worker",
                "route": route,
                "error_code": error_code,
                "safeguard_label": safeguard_label,
            }, ensure_ascii=False),
            "node": "worker",
            "trace_id": trace_id,
            "seq": seq,
        })

    def _save_checkpoint(
        self,
        thread_id: str,
        state: dict,
        metadata: dict,
    ) -> None:
        """체크포인터가 있으면 상태와 메타데이터를 저장한다."""
        save = getattr(self._checkpointer, "save", None)
        if callable(save):
            save(thread_id=thread_id, state=state, metadata=metadata)
