# 목적: 검색 결과를 병합한다.
# 설명: 정규화/중복 제거 규칙을 노드 내부에서 처리한다.
# 디자인 패턴: Command
# 참조: 없음

"""결과 병합 노드 모듈."""

from __future__ import annotations

from typing import Any


class MergeNode:
    """결과 병합 노드."""

    def __init__(self, top_k: int = 5, max_per_source: int = 2) -> None:
        """병합 규칙 설정을 초기화한다.

        Args:
            top_k: 최종 반환 상한 개수.
            max_per_source: source_id별 최대 허용 문서 수.
        """
        self._top_k = max(1, top_k)
        self._max_per_source = max(1, max_per_source)

    def run(self, groups: list[list[Any]]) -> list[Any]:
        """검색 결과를 병합한다.

        구현 내용:
            - 문서 타입을 공통 dict 구조로 정규화한다.
            - score_type이 distance면 similarity로 변환한다.
            - source_id/doc_id 기준 중복 제거를 적용한다.
            - source_id별 문서 편중을 제한한다.
            - 점수 기준 재정렬 후 top_k를 반환한다.
        """
        normalized = self._normalize_groups(groups)
        deduped = self._dedupe(normalized)
        diversified = self._diversify(deduped)
        diversified.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
        return diversified[: self._top_k]

    def _normalize_groups(self, groups: list[list[Any]]) -> list[dict[str, Any]]:
        """그룹 목록을 평탄화하고 공통 구조로 정규화한다."""
        result: list[dict[str, Any]] = []
        for group in groups:
            for doc in group:
                normalized = self._to_doc_dict(doc)
                normalized["score"] = self._normalize_score(
                    score=normalized.get("score"),
                    score_type=normalized.get("score_type"),
                )
                normalized["score_type"] = "similarity"
                result.append(normalized)
        return result

    def _to_doc_dict(self, doc: Any) -> dict[str, Any]:
        """문서 객체를 병합용 dict 구조로 변환한다."""
        if isinstance(doc, dict):
            metadata = doc.get("metadata")
            if not isinstance(metadata, dict):
                metadata = {}
            return {
                "doc_id": doc.get("doc_id") or doc.get("id"),
                "source_id": doc.get("source_id") or metadata.get("source_id") or doc.get("id"),
                "content": doc.get("content") or doc.get("page_content") or "",
                "metadata": metadata,
                "score": doc.get("score", 0.0),
                "score_type": doc.get("score_type") or metadata.get("score_type") or "similarity",
            }

        metadata = getattr(doc, "metadata", None)
        if not isinstance(metadata, dict):
            metadata = {}
        return {
            "doc_id": getattr(doc, "doc_id", None) or getattr(doc, "id", None),
            "source_id": metadata.get("source_id") or metadata.get("id"),
            "content": getattr(doc, "page_content", None) or str(doc),
            "metadata": metadata,
            "score": metadata.get("score", 0.0),
            "score_type": metadata.get("score_type", "similarity"),
        }

    def _normalize_score(self, score: Any, score_type: Any) -> float:
        """점수를 similarity 스케일로 정규화한다."""
        value = self._to_float(score)
        normalized_type = str(score_type or "similarity")
        if normalized_type == "distance":
            # distance -> similarity 단조 변환
            return 1.0 / (1.0 + max(value, 0.0))
        return value

    def _to_float(self, value: Any) -> float:
        """숫자/문자열 점수를 float로 변환한다."""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return 0.0
        return 0.0

    def _dedupe(self, docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """source_id/doc_id 기준 중복 제거를 수행한다."""
        deduped: list[dict[str, Any]] = []
        seen_keys: set[str] = set()
        for doc in docs:
            key = self._doc_key(doc)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            deduped.append(doc)
        return deduped

    def _diversify(self, docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """source_id 편중을 제한한다."""
        counts: dict[str, int] = {}
        diversified: list[dict[str, Any]] = []
        # 다양성 확보를 위해 우선 점수 정렬 후 제한을 적용한다.
        sorted_docs = sorted(docs, key=lambda item: float(item.get("score", 0.0)), reverse=True)
        for doc in sorted_docs:
            source_id = str(doc.get("source_id") or "unknown")
            count = counts.get(source_id, 0)
            if count >= self._max_per_source:
                continue
            counts[source_id] = count + 1
            diversified.append(doc)
        return diversified

    def _doc_key(self, doc: dict[str, Any]) -> str:
        """중복 제거용 문서 키를 반환한다."""
        source_id = doc.get("source_id")
        if source_id is not None:
            return f"source:{source_id}"
        doc_id = doc.get("doc_id")
        if doc_id is not None:
            return f"doc:{doc_id}"
        return f"content:{doc.get('content', '')}"
