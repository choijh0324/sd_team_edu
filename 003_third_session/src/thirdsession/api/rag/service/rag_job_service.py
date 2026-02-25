# 목적: 잡 서비스 인터페이스를 정의한다.
# 설명: 라우터가 호출할 서비스 메서드 시그니처를 제공한다.
# 디자인 패턴: 서비스 레이어 패턴
# 참조: nextStep.md

"""잡 서비스 모듈."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
import asyncio
import logging
from threading import Lock
from typing import Any
from uuid import uuid4

from thirdsession.api.rag.model import (
    JobCancelResponse,
    JobRequest,
    JobResponse,
    JobStatusResponse,
    JobStreamResponse,
)
from thirdsession.core.common.llm_client import LlmClient
from thirdsession.core.common.queue import ChatJobQueue, ChatStreamEventQueue
from thirdsession.core.common.sse_utils import parse_sse_line, to_sse_line
from thirdsession.core.rag.graphs.rag_pipeline_graph import RagPipelineGraph
from thirdsession.core.rag.nodes.stream_answer_node import StreamAnswerNode
from thirdsession.core.rag.nodes.stream_sources_node import StreamSourcesNode


LOGGER = logging.getLogger(__name__)


class RagJobService:
    """잡 서비스."""

    def __init__(
        self,
        job_queue: ChatJobQueue | None = None,
        event_queue: ChatStreamEventQueue | None = None,
        graph: RagPipelineGraph | None = None,
        llm_client: LlmClient | None = None,
    ) -> None:
        """서비스 의존성을 초기화한다.

        Args:
            job_queue: 작업 큐(선택).
            event_queue: 스트리밍 이벤트 큐(선택).
            graph: RAG 파이프라인 그래프(선택).
            llm_client: 스트리밍 답변 생성용 LLM 클라이언트(선택).
        """
        self._job_queue = job_queue
        self._event_queue = event_queue
        self._graph = graph
        self._jobs: dict[str, dict[str, Any]] = {}
        self._job_events: dict[str, list[JobStreamResponse]] = {}
        self._metrics_counter: Counter[str] = Counter()
        self._lock = Lock()
        self._stream_answer_node = StreamAnswerNode(llm_client=llm_client)
        self._stream_sources_node = StreamSourcesNode()

    def create_job(self, request: JobRequest) -> JobResponse:
        """잡 작업을 생성한다.

        TODO:
            - job_id/trace_id 생성
            - 워커 큐에 작업 적재
            - thread_id 기반 복구 로직 연결
            - 체크포인터에 thread_id 전달
            - safeguard 분기 결과를 error_code/metadata에 기록
            - 폴백 케이스에서도 스트리밍 이벤트 정상 종료
        """
        job_id = str(uuid4())
        trace_id = str(uuid4())
        thread_id = request.thread_id or f"thread-{job_id}"
        merged_metadata = dict(request.metadata or {})
        if request.collection is not None:
            merged_metadata["collection"] = request.collection
        if request.session_id is not None:
            merged_metadata["session_id"] = request.session_id
        if request.user_id is not None:
            merged_metadata["user_id"] = request.user_id

        with self._lock:
            self._jobs[job_id] = {
                "status": "queued",
                "trace_id": trace_id,
                "thread_id": thread_id,
                "query": request.query,
                "metadata": merged_metadata,
                "last_seq": 0,
                "canceled": False,
            }
            self._job_events[job_id] = []
            self._metrics_counter["job_created_total"] += 1

        payload = {
            "job_id": job_id,
            "trace_id": trace_id,
            "thread_id": thread_id,
            "query": request.query,
            "history": request.history or [],
            "turn_count": request.turn_count or 0,
            "session_id": request.session_id,
            "user_id": request.user_id,
            "metadata": merged_metadata,
        }
        self._try_enqueue_job(payload)

        return JobResponse(job_id=job_id, trace_id=trace_id, thread_id=thread_id)

    def stream_events(self, job_id: str) -> Iterable[str]:
        """스트리밍 이벤트를 SSE 라인으로 반환한다.

        TODO:
            - 이벤트 큐에서 이벤트 소비
            - done 이벤트까지 전송
            - seq는 job_id 기준으로 단조 증가
            - type/token/metadata/error/done 포맷 유지
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                error = JobStreamResponse(
                    type="error",
                    status="end",
                    content="존재하지 않는 job_id입니다.",
                )
                done = JobStreamResponse(type="DONE")
                return [self._to_sse_line(error), self._to_sse_line(done)]

            self._materialize_inmemory_result_if_needed(job_id=job_id)
            if not self._job_events.get(job_id):
                self._drain_event_queue_into_memory(job_id=job_id)
            events = list(self._job_events.get(job_id, []))
            self._metrics_counter["job_stream_total"] += 1
        return [self._to_sse_line(event) for event in events]

    def get_status(self, job_id: str) -> JobStatusResponse:
        """작업 상태를 조회한다.

        TODO:
            - 상태 저장소 조회
            - 진행률/상태 반환
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return JobStatusResponse(job_id=job_id, status="not_found", last_seq=None)
            if self._event_queue is not None:
                try:
                    queue_last_seq = asyncio.run(self._event_queue.get_last_seq(job_id))
                    if queue_last_seq > int(job["last_seq"]):
                        job["last_seq"] = queue_last_seq
                except Exception:
                    LOGGER.exception("큐 마지막 시퀀스 조회 실패: job_id=%s", job_id)
            return JobStatusResponse(
                job_id=job_id,
                status=str(job["status"]),
                last_seq=int(job["last_seq"]),
            )

    def cancel(self, job_id: str) -> JobCancelResponse:
        """작업을 취소한다.

        TODO:
            - 취소 플래그 기록
            - 워커가 취소를 확인하도록 구성
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return JobCancelResponse(job_id=job_id, status="not_found")
            if job["status"] in {"completed", "failed", "canceled"}:
                return JobCancelResponse(job_id=job_id, status=str(job["status"]))

            job["canceled"] = True
            job["status"] = "canceled"
            self._append_event(job_id, type_="error", status="end", content="작업이 취소되었습니다.")
            self._append_done_event(job_id)
            self._metrics_counter["job_canceled_total"] += 1
            return JobCancelResponse(job_id=job_id, status="canceled")

    def _try_enqueue_job(self, payload: dict[str, Any]) -> None:
        """구성된 작업 큐가 있으면 적재를 시도한다."""
        if self._job_queue is None:
            return
        try:
            asyncio.run(self._job_queue.push_job(payload))
        except NotImplementedError:
            LOGGER.info("job_queue 미구현으로 인메모리 모드로 동작합니다.")
        except Exception:
            LOGGER.exception("job_queue 적재 실패, 인메모리 모드로 계속 진행합니다.")

    def _materialize_inmemory_result_if_needed(self, job_id: str) -> None:
        """워커가 없을 때 스트리밍 결과를 인메모리로 생성한다."""
        job = self._jobs[job_id]
        if job["status"] in {"completed", "failed"}:
            return
        if job["status"] == "canceled":
            self._append_done_event(job_id)
            return

        job["status"] = "running"
        try:
            result_state = self._run_graph_or_fallback(job)

            # 1) answer token 스트리밍 이벤트 생성
            answer_lines = self._collect_async_events(
                self._stream_answer_node.run(
                    question=str(job["query"]),
                    contexts=result_state.get("contexts", []),
                    trace_id=str(job["trace_id"]),
                    seq_start=1,
                    prebuilt_answer=result_state.get("answer"),
                )
            )
            for line in answer_lines:
                payload = self._parse_sse_payload(line)
                if payload is None:
                    continue
                self._append_event_payload(job_id=job_id, payload=payload)

            # 2) references 스트리밍 이벤트 생성
            source_lines = self._collect_async_events(
                self._stream_sources_node.run(
                    sources=result_state.get("sources", []),
                    trace_id=str(job["trace_id"]),
                    seq_start=1,
                )
            )
            for line in source_lines:
                payload = self._parse_sse_payload(line)
                if payload is None:
                    continue
                self._append_event_payload(job_id=job_id, payload=payload)

            # 3) DONE 이벤트
            self._append_done_event(job_id)
            job["status"] = "completed"
            self._metrics_counter["job_completed_total"] += 1
        except Exception:
            LOGGER.exception("잡 스트리밍 이벤트 생성 실패: job_id=%s", job_id)
            job["status"] = "failed"
            self._append_event(
                job_id=job_id,
                type_="error",
                status="end",
                content="작업 처리 중 오류가 발생했습니다.",
            )
            self._append_done_event(job_id)

    def _append_event(
        self,
        job_id: str,
        type_: str,
        status: str | None = None,
        content: str | None = None,
        index: int | None = None,
        items: list[dict[str, Any]] | None = None,
        persist_queue: bool = True,
    ) -> None:
        """잡 이벤트를 저장소에 추가한다."""
        event = JobStreamResponse(
            type=type_,
            status=status,
            content=content,
            index=index,
            items=items,
        )
        self._job_events[job_id].append(event)
        self._jobs[job_id]["last_seq"] = len(self._job_events[job_id])

        if self._event_queue is None or not persist_queue:
            return
        try:
            asyncio.run(self._event_queue.push_event(job_id, event.model_dump(exclude_none=True)))
        except NotImplementedError:
            LOGGER.info("event_queue 미구현으로 인메모리 이벤트 저장소를 사용합니다.")
        except Exception:
            LOGGER.exception("event_queue 적재 실패, 인메모리 이벤트 저장소를 계속 사용합니다.")

    def _append_done_event(self, job_id: str) -> None:
        """종료 이벤트를 중복 없이 추가한다."""
        events = self._job_events.get(job_id, [])
        if events and events[-1].type == "DONE":
            return
        self._append_event(job_id, type_="DONE")

    def _run_graph_or_fallback(self, job: dict[str, Any]) -> dict[str, Any]:
        """그래프 실행 결과를 반환하고, 불가 시 폴백 결과를 생성한다."""
        if self._graph is None:
            return self._fallback_result_state(query=str(job["query"]))

        state = {
            "question": str(job["query"]),
            "history": [],
            "summary": None,
            "turn_count": 0,
            "contexts": [],
            "answer": None,
            "last_user_message": str(job["query"]),
            "last_assistant_message": None,
            "route": None,
            "error_code": None,
            "safeguard_label": None,
            "trace_id": str(job["trace_id"]),
            "thread_id": str(job["thread_id"]),
            "session_id": (job.get("metadata") or {}).get("session_id"),
            "user_id": (job.get("metadata") or {}).get("user_id"),
            "metadata": job.get("metadata") or {},
            "sources": [],
            "retrieval_stats": None,
        }
        result = self._graph.run(state)
        if result.get("sources"):
            return result
        return self._fallback_result_state(query=str(job["query"]))

    def _fallback_result_state(self, query: str) -> dict[str, Any]:
        """그래프 미연결 상태에서 사용할 기본 결과 상태를 생성한다."""
        return {
            "contexts": [],
            "sources": [
                {
                    "source_id": "system:placeholder",
                    "title": "작업 큐 스캐폴딩",
                    "content": f"질문: {query}",
                    "score": 0.0,
                    "metadata": {},
                }
            ],
        }

    def _collect_async_events(self, stream: Any) -> list[str]:
        """비동기 이터레이터를 동기 컨텍스트에서 수집한다."""
        async def collect() -> list[str]:
            lines: list[str] = []
            async for line in stream:
                lines.append(line)
            return lines

        return asyncio.run(collect())

    def _parse_sse_payload(self, line: str) -> dict[str, Any] | None:
        """SSE 라인에서 JSON payload를 추출한다."""
        return parse_sse_line(line)

    def _append_event_payload(self, job_id: str, payload: dict[str, Any]) -> None:
        """payload 딕셔너리를 JobStreamResponse 이벤트로 변환해 적재한다."""
        self._append_event(
            job_id=job_id,
            type_=str(payload.get("type")),
            status=payload.get("status"),
            content=payload.get("content"),
            index=payload.get("index"),
            items=payload.get("items"),
        )

    def _drain_event_queue_into_memory(self, job_id: str) -> None:
        """외부 이벤트 큐에 누적된 이벤트를 인메모리 저장소로 동기화한다."""
        if self._event_queue is None:
            return

        async def drain() -> list[dict[str, Any]]:
            drained: list[dict[str, Any]] = []
            while True:
                event = await self._event_queue.pop_event(job_id)
                if event is None:
                    break
                drained.append(event)
            return drained

        try:
            drained_events = asyncio.run(drain())
        except Exception:
            LOGGER.exception("이벤트 큐 소비 실패: job_id=%s", job_id)
            return

        for payload in drained_events:
            self._append_event(
                job_id=job_id,
                type_=str(payload.get("type")),
                status=payload.get("status"),
                content=payload.get("content"),
                index=payload.get("index"),
                items=payload.get("items"),
                persist_queue=False,
            )

    def _to_sse_line(self, event: JobStreamResponse) -> str:
        """SSE 한 줄 포맷으로 직렬화한다."""
        return to_sse_line(event.model_dump(exclude_none=True))
