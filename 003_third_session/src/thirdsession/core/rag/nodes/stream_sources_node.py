# 목적: 근거 문서 스트리밍을 수행한다.
# 설명: 답변 이후 근거를 전송하는 규칙을 담당한다.
# 디자인 패턴: Command
# 참조: thirdsession/api/rag/model/chat_stream_event.py

"""근거 스트리밍 노드 모듈."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from thirdsession.core.common.sse_utils import to_sse_line

# TODO: 스트리밍 이벤트/메타데이터/소스 모델을 연결한다.


class StreamSourcesNode:
    """근거 스트리밍 노드."""

    async def run(
        self,
        sources: list[Any],
        trace_id: str,
        seq_start: int,
        node: str | None = "stream_sources",
    ) -> AsyncIterator[str]:
        """근거 문서를 스트리밍한다.

        Args:
            sources: 근거 문서 목록(직렬화 가능 구조).
            trace_id: 스트리밍 추적 식별자.
            seq_start: 시작 시퀀스 번호.
            node: 노드 식별자(선택).

        Yields:
            str: SSE 데이터 라인.
        """
        normalized_sources = self._normalize_sources(sources)
        _ = trace_id
        _ = node
        _ = seq_start

        yield self._to_sse_line(
            {
                "type": "references",
                "status": "end",
                "items": normalized_sources,
            }
        )

    def _normalize_sources(self, sources: list[Any]) -> list[Any]:
        """근거 문서 목록을 RagSourceItem으로 정규화한다."""
        normalized: list[dict[str, Any]] = []
        for index, source in enumerate(sources, start=1):
            if isinstance(source, dict):
                normalized.append(self._from_dict(source, index))
                continue
            if hasattr(source, "page_content") or hasattr(source, "metadata"):
                normalized.append(self._from_document(source, index))
                continue
            normalized.append(self._from_unknown(source, index))
        return normalized

    def _from_dict(self, payload: dict[str, Any], index: int) -> dict[str, Any]:
        """dict 기반 소스를 RagSourceItem으로 변환한다."""
        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}

        source_id = payload.get("source_id") or payload.get("id") or metadata.get("source_id") or f"source-{index}"
        title = payload.get("title") or metadata.get("title")
        snippet = payload.get("snippet") or payload.get("content") or payload.get("page_content")
        score = payload.get("score")
        return {
            "source_id": str(source_id),
            "title": title,
            "snippet": str(snippet)[:300] if snippet is not None else None,
            "score": self._to_float(score),
            "metadata": metadata,
        }

    def _from_unknown(self, source: Any, index: int) -> dict[str, Any]:
        """알 수 없는 타입을 기본 구조로 변환한다."""
        text = str(source)
        return {
            "source_id": f"source-{index}",
            "title": None,
            "snippet": text[:300],
            "score": 0.0,
            "metadata": {},
        }

    def _from_document(self, document: Any, index: int) -> dict[str, Any]:
        """DocumentModel을 RagSourceItem으로 변환한다."""
        metadata = getattr(document, "metadata", None)
        if not isinstance(metadata, dict):
            metadata = {}

        page_content = getattr(document, "page_content", None)
        source_id = metadata.get("source_id") or metadata.get("id") or f"source-{index}"
        title = metadata.get("title")
        score = metadata.get("score")
        return {
            "source_id": str(source_id),
            "title": title,
            "snippet": str(page_content)[:300] if page_content is not None else None,
            "score": self._to_float(score),
            "metadata": metadata,
        }

    def _to_float(self, value: Any) -> float:
        """점수 값을 float로 변환한다."""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return 0.0
        return 0.0

    def _to_sse_line(self, payload: dict[str, Any]) -> str:
        """SSE 라인 문자열로 직렬화한다."""
        return to_sse_line(payload)
