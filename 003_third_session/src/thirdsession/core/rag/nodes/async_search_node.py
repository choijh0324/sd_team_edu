# 목적: 비동기 검색을 수행한다.
# 설명: 하위 쿼리를 병렬로 실행하며 임베딩/벡터 검색 로직을 노드 내부에서 처리한다.
# 디자인 패턴: Command
# 참조: thirdsession/core/rag/graphs/query_decompose_graph.py

"""비동기 검색 노드 모듈."""

from __future__ import annotations

import asyncio
from typing import Any


class AsyncSearchNode:
    """비동기 검색 노드."""

    def __init__(self, max_concurrency: int = 4, timeout_seconds: float = 10.0) -> None:
        """노드 실행 설정을 초기화한다.

        Args:
            max_concurrency: 동시 실행 검색 수 제한.
            timeout_seconds: 단일 검색 타임아웃(초).
        """
        self._max_concurrency = max(1, max_concurrency)
        self._timeout_seconds = max(0.1, timeout_seconds)

    async def run(self, queries: list[str], retriever: Any) -> list[list[Any]]:
        """쿼리 목록을 비동기로 검색한다.

        구현 내용:
            - 중복/공백 쿼리를 정리한다.
            - 세마포어로 동시성 상한을 제어한다.
            - 검색 실패/타임아웃은 해당 쿼리 결과를 빈 목록으로 처리한다.
            - 결과를 공통 dict 형태로 정규화한다.
        """
        normalized_queries = self._normalize_queries(queries)
        if not normalized_queries:
            return []
        if retriever is None:
            return [[] for _ in normalized_queries]

        semaphore = asyncio.Semaphore(self._max_concurrency)

        async def search_one(query: str) -> list[Any]:
            async with semaphore:
                try:
                    docs = await asyncio.wait_for(
                        self._search_with_retriever(query=query, retriever=retriever),
                        timeout=self._timeout_seconds,
                    )
                except Exception:
                    return []
                return [self._normalize_doc(doc=doc, query=query) for doc in docs]

        results = await asyncio.gather(*[search_one(query) for query in normalized_queries])
        return results

    def _normalize_queries(self, queries: list[str]) -> list[str]:
        """입력 쿼리를 정규화한다."""
        normalized: list[str] = []
        for query in queries:
            text = " ".join(query.split())
            if text == "":
                continue
            if text in normalized:
                continue
            normalized.append(text)
        return normalized

    async def _search_with_retriever(self, query: str, retriever: Any) -> list[Any]:
        """Retriever 인터페이스를 자동 감지해 검색을 수행한다."""
        if hasattr(retriever, "ainvoke"):
            result = retriever.ainvoke(query)
            docs = await result if asyncio.iscoroutine(result) else result
            return self._to_list(docs)

        if hasattr(retriever, "aget_relevant_documents"):
            docs = await retriever.aget_relevant_documents(query)
            return self._to_list(docs)

        if hasattr(retriever, "invoke"):
            docs = await asyncio.to_thread(retriever.invoke, query)
            return self._to_list(docs)

        if hasattr(retriever, "get_relevant_documents"):
            docs = await asyncio.to_thread(retriever.get_relevant_documents, query)
            return self._to_list(docs)

        return []

    def _to_list(self, docs: Any) -> list[Any]:
        """검색 결과를 리스트로 변환한다."""
        if docs is None:
            return []
        if isinstance(docs, list):
            return docs
        if isinstance(docs, tuple):
            return list(docs)
        return [docs]

    def _normalize_doc(self, doc: Any, query: str) -> dict[str, Any]:
        """문서 타입을 공통 딕셔너리 구조로 정규화한다."""
        if isinstance(doc, dict):
            metadata = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
            score = self._extract_score(doc=doc, metadata=metadata)
            score_type = self._extract_score_type(doc=doc, metadata=metadata)
            source_id = doc.get("source_id") or doc.get("id") or metadata.get("source_id")
            return {
                "doc_id": doc.get("doc_id") or doc.get("id"),
                "source_id": source_id,
                "content": doc.get("content") or doc.get("page_content") or "",
                "metadata": metadata,
                "score": score,
                "score_type": score_type,
                "retrieval_query": query,
            }

        metadata = getattr(doc, "metadata", None)
        if not isinstance(metadata, dict):
            metadata = {}
        page_content = getattr(doc, "page_content", None)
        score = self._extract_score(doc=None, metadata=metadata)
        score_type = self._extract_score_type(doc=None, metadata=metadata)
        source_id = metadata.get("source_id") or metadata.get("id")
        return {
            "doc_id": getattr(doc, "id", None),
            "source_id": source_id,
            "content": page_content or str(doc),
            "metadata": metadata,
            "score": score,
            "score_type": score_type,
            "retrieval_query": query,
        }

    def _extract_score(self, doc: dict[str, Any] | None, metadata: dict[str, Any]) -> float:
        """점수를 추출한다."""
        candidates: list[Any] = []
        if doc is not None:
            candidates.extend([doc.get("score"), doc.get("similarity"), doc.get("distance")])
        candidates.extend([metadata.get("score"), metadata.get("similarity"), metadata.get("distance")])
        for value in candidates:
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                try:
                    return float(value)
                except ValueError:
                    continue
        return 0.0

    def _extract_score_type(self, doc: dict[str, Any] | None, metadata: dict[str, Any]) -> str:
        """점수 타입(distance/similarity)을 추출한다."""
        if doc is not None:
            score_type = doc.get("score_type")
            if isinstance(score_type, str) and score_type in {"distance", "similarity"}:
                return score_type
            if doc.get("distance") is not None:
                return "distance"
            if doc.get("similarity") is not None:
                return "similarity"
        meta_type = metadata.get("score_type")
        if isinstance(meta_type, str) and meta_type in {"distance", "similarity"}:
            return meta_type
        if metadata.get("distance") is not None:
            return "distance"
        return "similarity"
