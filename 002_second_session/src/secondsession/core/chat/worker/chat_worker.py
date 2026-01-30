# 목적: 대화 워커 실행 흐름을 정의한다.
# 설명: 큐 소비 → 그래프 실행 → 스트리밍 이벤트 적재를 담당한다.
# 디자인 패턴: Worker, Producer-Consumer, Template Method(상속)
# 참조: docs/02_backend_service_layer/05_비동기_엔드포인트_분리_전략.md

"""대화 워커 모듈."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import re
from typing import Any

from secondsession.api.chat.const import MetadataEventType, StreamEventType
from secondsession.core.chat.const import ErrorCode, SafeguardLabel
from secondsession.core.chat.graphs import ChatGraph
from secondsession.core.chat.state.chat_state import ChatState
from secondsession.core.common.queue import ChatJobQueue, ChatStreamEventQueue
from secondsession.core.common.worker import WorkerBase


class ChatWorker(WorkerBase):
    """대화 워커."""

    def __init__(
        self,
        job_queue: ChatJobQueue,
        event_queue: ChatStreamEventQueue,
        checkpointer: Any,
        redis_client: Any,
        poll_interval: float = 0.1,
    ) -> None:
        """워커를 초기화한다.

        Args:
            job_queue: 대화 작업 큐.
            event_queue: 스트리밍 이벤트 큐.
            checkpointer: LangGraph 체크포인터.
            redis_client: Redis 클라이언트.
            poll_interval: 큐 폴링 간격(초).
        """
        super().__init__(poll_interval=poll_interval)
        self._job_queue = job_queue
        self._event_queue = event_queue
        self._checkpointer = checkpointer
        self._redis = redis_client

    def _dequeue_job(self) -> dict | None:
        """큐에서 작업을 꺼낸다."""
        return self._job_queue.dequeue()

    def _process_job(self, job: dict) -> None:
        """단일 작업을 처리한다.

        구현 내용:
            - 그래프 실행 및 token/metadata/error/done 이벤트 적재
            - 취소 플래그 확인 및 error → done 순서 보장
        """
        logger = logging.getLogger(__name__)
        job_id = str(job.get("job_id"))
        trace_id = str(job.get("trace_id"))
        thread_id = str(job.get("thread_id"))
        session_id = job.get("session_id")
        seq = 1

        logger.info("작업 시작 job_id=%s trace_id=%s", job_id, trace_id)

        if self._is_cancelled(job_id):
            self._set_status(job_id, "cancelled")
            self._event_queue.push_event(
                job_id,
                self._build_error_event(
                    trace_id=trace_id,
                    seq=seq,
                    content=ErrorCode.CANCELLED.user_message,
                    error_code=ErrorCode.CANCELLED,
                ),
            )
            seq += 1
            self._event_queue.push_event(
                job_id,
                self._build_done_event(trace_id=trace_id, seq=seq),
            )
            logger.info("작업 취소됨 job_id=%s", job_id)
            return

        self._set_status(job_id, "running")
        graph = ChatGraph(checkpointer=self._checkpointer)
        state: ChatState = {
            "history": job.get("history", []),
            "summary": None,
            "turn_count": job.get("turn_count", 0),
            "last_user_message": job.get("query", ""),
            "last_assistant_message": None,
            "candidates": [],
            "candidate_scores": [],
            "candidate_errors": [],
            "selected_candidate": None,
            "safeguard_label": None,
            "route": None,
            "error_code": None,
            "trace_id": trace_id,
            "thread_id": thread_id,
            "session_id": session_id,
            "history_persisted": None,
            "checkpoint_ref": job.get("checkpoint_id"),
        }

        self._event_queue.push_event(
            job_id,
            self._build_metadata_event(
                trace_id=trace_id,
                seq=seq,
                event=MetadataEventType.JOB_START,
                message="작업을 시작합니다.",
            ),
        )
        seq += 1

        try:
            result = graph.run(state)
            assistant_message = result.get("last_assistant_message")
            if self._is_cancelled(job_id):
                self._set_status(job_id, "cancelled")
                self._event_queue.push_event(
                    job_id,
                    self._build_error_event(
                        trace_id=trace_id,
                        seq=seq,
                        content=ErrorCode.CANCELLED.user_message,
                        error_code=ErrorCode.CANCELLED,
                    ),
                )
                seq += 1
                logger.info("작업 취소됨 job_id=%s", job_id)
                return
            route = result.get("route")
            safeguard_label = result.get("safeguard_label")
            error_code = self._resolve_error_code(result.get("error_code"), safeguard_label)
            if error_code is not None:
                self._event_queue.push_event(
                    job_id,
                    self._build_error_event(
                        trace_id=trace_id,
                        seq=seq,
                        content=self._error_message(error_code),
                        error_code=error_code,
                    ),
                )
                seq += 1
            if route or safeguard_label or error_code:
                self._event_queue.push_event(
                    job_id,
                    self._build_metadata_event(
                        trace_id=trace_id,
                        seq=seq,
                        event=MetadataEventType.ROUTE_DECISION,
                        message="라우팅 결과가 결정되었습니다.",
                        route=route,
                        error_code=error_code,
                        safeguard_label=safeguard_label,
                    ),
                )
                seq += 1
            if assistant_message:
                for token in self._iter_tokens(str(assistant_message)):
                    if self._should_cancel(job_id, trace_id, seq):
                        return
                    self._event_queue.push_event(
                        job_id,
                        self._build_token_event(
                            trace_id=trace_id,
                            seq=seq,
                            content=token,
                        ),
                    )
                    seq += 1
            self._event_queue.push_event(
                job_id,
                self._build_metadata_event(
                    trace_id=trace_id,
                    seq=seq,
                    event=MetadataEventType.JOB_END,
                    message="작업이 종료되었습니다.",
                ),
            )
            seq += 1
            self._set_status(job_id, "done")
            logger.info("작업 완료 job_id=%s", job_id)
        except Exception as exc:  # pragma: no cover - 외부 의존성
            self._set_status(job_id, "failed")
            logger.exception("작업 실패 job_id=%s error=%s", job_id, exc)
            self._event_queue.push_event(
                job_id,
                self._build_error_event(
                    trace_id=trace_id,
                    seq=seq,
                    content=str(exc),
                    error_code=ErrorCode.UNKNOWN,
                ),
            )
            seq += 1
        finally:
            self._event_queue.push_event(
                job_id,
                self._build_done_event(trace_id=trace_id, seq=seq),
            )

    def _build_token_event(self, trace_id: str, seq: int, content: str) -> dict:
        """token 이벤트를 생성한다."""
        return {
            "type": StreamEventType.TOKEN.value,
            "trace_id": trace_id,
            "seq": seq,
            "content": content,
        }

    def _iter_tokens(self, content: str) -> list[str]:
        """응답을 토큰 단위로 분해한다."""
        if not content:
            return []
        tokens = re.findall(r"\S+\s*", content)
        return tokens if tokens else [content]

    def _build_error_event(
        self,
        trace_id: str,
        seq: int,
        content: str,
        error_code: ErrorCode | str,
    ) -> dict:
        """error 이벤트를 생성한다."""
        if isinstance(error_code, ErrorCode):
            error_code_value = error_code.code
        else:
            error_code_value = str(error_code)
        return {
            "type": StreamEventType.ERROR.value,
            "trace_id": trace_id,
            "seq": seq,
            "content": content,
            "error_code": error_code_value,
        }

    def _build_done_event(self, trace_id: str, seq: int) -> dict:
        """done 이벤트를 생성한다."""
        return {
            "type": StreamEventType.DONE.value,
            "trace_id": trace_id,
            "seq": seq,
            "content": None,
        }

    def _build_metadata_event(
        self,
        trace_id: str,
        seq: int,
        event: MetadataEventType,
        message: str,
        route: str | None = None,
        error_code: ErrorCode | str | None = None,
        safeguard_label: SafeguardLabel | str | None = None,
        node: str | None = None,
    ) -> dict:
        """metadata 이벤트를 생성한다."""
        metadata: dict[str, Any] = {
            "event": event.value,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if node:
            metadata["node"] = node
        if route:
            metadata["route"] = route
        if error_code is not None:
            if isinstance(error_code, ErrorCode):
                metadata["error_code"] = error_code.code
            else:
                metadata["error_code"] = str(error_code)
        if safeguard_label is not None:
            if isinstance(safeguard_label, SafeguardLabel):
                metadata["safeguard_label"] = safeguard_label.value
            else:
                metadata["safeguard_label"] = str(safeguard_label)
        return {
            "type": StreamEventType.METADATA.value,
            "trace_id": trace_id,
            "seq": seq,
            "metadata": metadata,
        }

    def _resolve_error_code(
        self,
        value: ErrorCode | str | None,
        safeguard_label: SafeguardLabel | str | None,
    ) -> ErrorCode | str | None:
        """에러 코드를 정규화한다."""
        if isinstance(value, ErrorCode):
            return value
        if isinstance(value, str):
            for code in ErrorCode:
                if code.code == value:
                    return code
            return value
        if self._is_blocked_label(safeguard_label):
            return ErrorCode.SAFEGUARD
        return None

    def _is_blocked_label(self, label: SafeguardLabel | str | None) -> bool:
        """차단 라벨 여부를 판단한다."""
        if label is None:
            return False
        if isinstance(label, SafeguardLabel):
            return label != SafeguardLabel.PASS
        return str(label).upper() != SafeguardLabel.PASS.value

    def _error_message(self, error_code: ErrorCode | str) -> str:
        """에러 메시지를 생성한다."""
        if isinstance(error_code, ErrorCode):
            return error_code.user_message
        return str(error_code)

    def _is_cancelled(self, job_id: str) -> bool:
        """취소 플래그를 확인한다."""
        key = f"chat:cancel:{job_id}"
        return bool(self._redis.get(key))

    def _should_cancel(self, job_id: str, trace_id: str, seq: int) -> bool:
        """취소 여부를 확인하고 취소 이벤트를 전송한다."""
        if not self._is_cancelled(job_id):
            return False
        self._set_status(job_id, "cancelled")
        self._event_queue.push_event(
            job_id,
            self._build_error_event(
                trace_id=trace_id,
                seq=seq,
                content=ErrorCode.CANCELLED.user_message,
                error_code=ErrorCode.CANCELLED,
            ),
        )
        return True

    def _set_status(self, job_id: str, status: str) -> None:
        """작업 상태를 저장한다."""
        key = f"chat:status:{job_id}"
        self._redis.set(key, status)
