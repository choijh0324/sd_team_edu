# 목적: 후처리 단계를 실행한다.
# 설명: 중복 제거/다양성/재정렬/압축을 노드 내부에서 수행한다.
# 디자인 패턴: Command
# 참조: 없음

"""후처리 노드 모듈."""

from __future__ import annotations

from typing import Any


class PostprocessNode:
    """후처리 노드."""

    def __init__(
        self,
        top_k: int = 5,
        max_per_source: int = 2,
        max_chars_per_doc: int = 500,
    ) -> None:
        """후처리 설정을 초기화한다.

        Args:
            top_k: 최종 반환 상한 개수.
            max_per_source: source_id별 최대 허용 문서 수.
            max_chars_per_doc: 문서 본문 최대 길이.
        """
        self._top_k = max(1, top_k)
        self._max_per_source = max(1, max_per_source)
        self._max_chars_per_doc = max(100, max_chars_per_doc)

    def run(self, docs: list[Any]) -> list[Any]:
        """후처리를 수행한다.

        구현 순서:
            1) 타입 정규화
            2) 중복 제거(source_id/doc_id/content 기준)
            3) 다양성 확보(source_id별 개수 제한)
            4) 점수 재정렬
            5) 컨텍스트 압축(본문 길이 제한)
            6) top_k 제한
        """
        normalized = [self._to_doc_dict(doc) for doc in docs]
        deduped = self._dedupe(normalized)
        diversified = self._diversify(deduped)
        reranked = sorted(diversified, key=lambda item: float(item.get("score", 0.0)), reverse=True)
        compressed = [self._compress_doc(doc) for doc in reranked]
        return compressed[: self._top_k]

    def _to_doc_dict(self, doc: Any) -> dict[str, Any]:
        """문서 객체를 공통 딕셔너리 구조로 변환한다."""
        if isinstance(doc, dict):
            metadata = doc.get("metadata")
            if not isinstance(metadata, dict):
                metadata = {}
            return {
                "doc_id": doc.get("doc_id") or doc.get("id"),
                "source_id": doc.get("source_id") or metadata.get("source_id") or doc.get("id"),
                "title": doc.get("title"),
                "content": doc.get("content") or doc.get("page_content") or "",
                "snippet": doc.get("snippet"),
                "metadata": metadata,
                "score": self._to_float(doc.get("score")),
                "score_type": doc.get("score_type") or metadata.get("score_type") or "similarity",
            }

        metadata = getattr(doc, "metadata", None)
        if not isinstance(metadata, dict):
            metadata = {}
        page_content = getattr(doc, "page_content", None)
        return {
            "doc_id": getattr(doc, "doc_id", None) or getattr(doc, "id", None),
            "source_id": metadata.get("source_id") or metadata.get("id"),
            "title": metadata.get("title"),
            "content": page_content or str(doc),
            "snippet": None,
            "metadata": metadata,
            "score": self._to_float(metadata.get("score")),
            "score_type": metadata.get("score_type", "similarity"),
        }

    def _to_float(self, value: Any) -> float:
        """숫자/문자열 값을 float로 변환한다."""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return 0.0
        return 0.0

    def _dedupe(self, docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """중복 문서를 제거한다."""
        result: list[dict[str, Any]] = []
        seen: set[str] = set()
        for doc in docs:
            key = self._doc_key(doc)
            if key in seen:
                continue
            seen.add(key)
            result.append(doc)
        return result

    def _doc_key(self, doc: dict[str, Any]) -> str:
        """중복 제거용 키를 생성한다."""
        source_id = doc.get("source_id")
        if source_id is not None:
            return f"source:{source_id}"
        doc_id = doc.get("doc_id")
        if doc_id is not None:
            return f"doc:{doc_id}"
        return f"content:{doc.get('content', '')}"

    def _diversify(self, docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """출처 편중을 완화한다."""
        counts: dict[str, int] = {}
        result: list[dict[str, Any]] = []
        for doc in sorted(docs, key=lambda item: float(item.get("score", 0.0)), reverse=True):
            source_id = str(doc.get("source_id") or "unknown")
            current = counts.get(source_id, 0)
            if current >= self._max_per_source:
                continue
            counts[source_id] = current + 1
            result.append(doc)
        return result

    def _compress_doc(self, doc: dict[str, Any]) -> dict[str, Any]:
        """컨텍스트 길이를 제한한다."""
        compact = dict(doc)
        content = str(compact.get("content") or "")
        compact["content"] = " ".join(content.split())[: self._max_chars_per_doc]
        return compact
