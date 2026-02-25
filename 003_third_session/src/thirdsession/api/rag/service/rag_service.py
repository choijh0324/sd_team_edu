# 목적: rag 서비스 그래프 호출을 담당한다.
# 설명: API 계층에서 코어 그래프를 호출하고 응답 모델로 변환한다.
# 디자인 패턴: Service
# 참조: thirdsession/core/rag/graphs/rag_pipeline_graph.py

"""rag 서비스 모듈."""

from __future__ import annotations

from collections.abc import AsyncIterator
from collections import Counter
import logging
from time import perf_counter
from typing import Any
from uuid import uuid4

from thirdsession.api.rag.model.request import RagRequest
from thirdsession.api.rag.model.response import (
    RagDetailPayload,
    RagMetaPayload,
    RagResponse,
    RagSourceItem,
    RagSummaryPayload,
)
from thirdsession.core.common.sse_utils import done_sse_line
from thirdsession.core.rag.const.error_code import ErrorCode
from thirdsession.core.rag.graphs.rag_pipeline_graph import RagPipelineGraph
from thirdsession.core.rag.nodes.stream_answer_node import StreamAnswerNode
from thirdsession.core.rag.nodes.stream_sources_node import StreamSourcesNode
from thirdsession.core.rag.state.chat_state import ChatState


LOGGER = logging.getLogger(__name__)


class RagService:
    """rag 서비스 클래스."""

    def __init__(self, graph: RagPipelineGraph) -> None:
        """서비스 의존성을 초기화한다.

        Args:
            graph: rag 그래프 실행기.
        """
        self._graph = graph
        self._metrics_counter: Counter[str] = Counter()
        self._latency_samples_ms: list[float] = []
        self._stream_answer_node = StreamAnswerNode()
        self._stream_sources_node = StreamSourcesNode()

    def handle(self, request: RagRequest) -> RagResponse:
        """rag 요청을 처리한다.

        Args:
            request: rag 요청 모델.

        Returns:
            RagResponse: 응답 모델.
        """
        state = self._to_initial_state(request)
        trace_id = state["trace_id"] or "unknown"
        started = perf_counter()
        self._record_count("rag_handle_total")
        try:
            result_state = self._graph.run(state)
            response = self._to_response(result_state)
            self._record_count("rag_handle_success_total")
            return response
        except Exception as error:
            mapped_error = ErrorCode.from_exception(error)
            self._record_count("rag_handle_error_total")
            LOGGER.exception(
                "RAG 처리 실패: trace_id=%s error_code=%s",
                trace_id,
                mapped_error.code,
            )
            return RagResponse(
                answer=mapped_error.user_message,
                citations=[],
                trace_id=trace_id,
                summary=RagSummaryPayload(
                    answer=mapped_error.user_message,
                    citations=[],
                ),
                detail=RagDetailPayload(
                    question=request.question,
                    answer=mapped_error.user_message,
                    sources=[],
                    error_code=mapped_error.code,
                ),
                meta=RagMetaPayload(
                    trace_id=trace_id,
                    user_id=request.user_id,
                    metadata=request.metadata,
                ),
            )
        finally:
            self._record_latency_ms((perf_counter() - started) * 1000.0)

    async def stream(self, request: RagRequest) -> AsyncIterator[str]:
        """rag 스트리밍을 처리한다.

        Args:
            request: rag 요청 모델.

        Yields:
            str: SSE 이벤트 라인.
        """
        state = self._to_initial_state(request)
        trace_id = state["trace_id"] or "unknown"
        self._record_count("rag_stream_total")
        try:
            result_state = self._graph.run(state)
            contexts = result_state.get("contexts", [])
            sources = result_state.get("sources", [])

            # 순서 보장 1: 답변 토큰 스트리밍
            async for event_line in self._stream_answer_node.run(
                question=request.question,
                contexts=contexts,
                trace_id=trace_id,
                seq_start=1,
                prebuilt_answer=result_state.get("answer"),
            ):
                yield event_line

            # 순서 보장 2: 근거 스트리밍
            async for event_line in self._stream_sources_node.run(
                sources=sources,
                trace_id=trace_id,
                seq_start=1,
            ):
                yield event_line

            self._record_count("rag_stream_success_total")
        except Exception as error:
            mapped_error = ErrorCode.from_exception(error)
            self._record_count("rag_stream_error_total")
            LOGGER.exception(
                "RAG 스트리밍 실패: trace_id=%s error_code=%s",
                trace_id,
                mapped_error.code,
            )
            # 실패 시에도 순서(answer -> references -> DONE)를 유지한다.
            async for event_line in self._stream_answer_node.run(
                question=request.question,
                contexts=[],
                trace_id=trace_id,
                seq_start=1,
            ):
                yield event_line
            async for event_line in self._stream_sources_node.run(
                sources=[],
                trace_id=trace_id,
                seq_start=1,
            ):
                yield event_line
        finally:
            # 순서 보장 3: done 이벤트
            yield self._to_done_sse_line()

    # TODO: 요청 → 상태 변환 로직을 분리한다.
    # TODO: 컨텍스트 → 근거 소스 변환 로직을 분리한다.

    def _to_initial_state(self, request: RagRequest) -> ChatState:
        """요청 모델을 그래프 입력 상태로 변환한다."""
        incoming_metadata = request.metadata or {}
        trace_id = self._resolve_trace_id(incoming_metadata)
        return ChatState(
            question=request.question,
            history=[],
            summary=None,
            turn_count=0,
            contexts=[],
            answer=None,
            last_user_message=request.question,
            last_assistant_message=None,
            route=None,
            error_code=None,
            safeguard_label=None,
            trace_id=trace_id,
            thread_id=incoming_metadata.get("thread_id"),
            session_id=incoming_metadata.get("session_id"),
            user_id=request.user_id,
            metadata=incoming_metadata,
            sources=[],
            retrieval_stats=None,
        )

    def _to_response(self, state: ChatState) -> RagResponse:
        """그래프 결과 상태를 API 응답 모델로 변환한다."""
        state_error = ErrorCode.from_code(state.get("error_code"))
        answer = state.get("answer") or state_error.user_message
        summary_answer = state.get("summary") or answer
        normalized_sources = self._normalize_sources(state.get("sources"))
        citations = self._extract_citations(state.get("sources"))
        trace_id = state.get("trace_id")
        return RagResponse(
            answer=answer,
            citations=citations,
            trace_id=trace_id,
            summary=RagSummaryPayload(
                answer=summary_answer,
                citations=citations,
            ),
            detail=RagDetailPayload(
                question=state.get("question"),
                answer=answer,
                sources=[RagSourceItem(**source) for source in normalized_sources],
                error_code=state_error.code if state.get("error_code") else None,
                safeguard_label=state.get("safeguard_label"),
            ),
            meta=RagMetaPayload(
                trace_id=trace_id,
                thread_id=state.get("thread_id"),
                session_id=state.get("session_id"),
                user_id=state.get("user_id"),
                route=state.get("route"),
                retrieval_stats=state.get("retrieval_stats"),
                metadata=state.get("metadata"),
            ),
        )

    def _extract_citations(self, sources: list[dict[str, Any]] | None) -> list[str]:
        """근거 목록에서 citation 식별자 목록을 추출한다."""
        if not sources:
            return []
        result: list[str] = []
        for index, source in enumerate(sources):
            source_id = source.get("source_id") or source.get("id") or f"source-{index + 1}"
            result.append(str(source_id))
        return result

    def _normalize_sources(self, sources: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
        """스트리밍 전송용 근거 목록을 정규화한다."""
        if not sources:
            return []
        normalized: list[dict[str, Any]] = []
        for index, source in enumerate(sources):
            normalized.append(
                {
                    "source_id": str(source.get("source_id") or source.get("id") or f"source-{index + 1}"),
                    "title": source.get("title"),
                    "snippet": source.get("snippet") or source.get("content"),
                    "score": source.get("score"),
                    "metadata": source.get("metadata"),
                }
            )
        return normalized

    def _to_done_sse_line(self) -> str:
        """스트리밍 종료(DONE) SSE 라인을 생성한다."""
        return done_sse_line()

    def _resolve_trace_id(self, metadata: dict[str, Any]) -> str:
        """요청 메타데이터에서 trace_id를 가져오거나 새로 생성한다."""
        raw_trace_id = metadata.get("trace_id")
        if isinstance(raw_trace_id, str) and raw_trace_id.strip() != "":
            return raw_trace_id
        return str(uuid4())

    def _record_count(self, name: str) -> None:
        """간단한 카운터 메트릭을 누적한다."""
        self._metrics_counter[name] += 1

    def _record_latency_ms(self, latency_ms: float) -> None:
        """요청 지연 시간을 기록한다."""
        self._latency_samples_ms.append(latency_ms)
