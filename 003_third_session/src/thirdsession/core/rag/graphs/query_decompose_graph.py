# 목적: 쿼리 분해 기반 그래프를 정의한다.
# 설명: 질문 분해 → 병렬 검색 → 병합 흐름을 캡슐화한다.
# 디자인 패턴: State Machine
# 참조: thirdsession/core/rag/nodes/query_decompose_node.py

"""쿼리 분해 그래프 모듈."""

from __future__ import annotations

import asyncio
import re
from threading import Thread
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from thirdsession.core.common.llm_client import LlmClient
from thirdsession.core.rag.nodes.async_search_node import AsyncSearchNode
from thirdsession.core.rag.nodes.merge_node import MergeNode
from thirdsession.core.rag.nodes.query_decompose_node import QueryDecomposeNode


class QueryDecomposeState(TypedDict, total=False):
    """쿼리 분해 그래프 상태."""

    question: str
    retriever: Any
    sub_queries: list[str]
    search_groups: list[list[Any]]
    verified_groups: list[list[Any]]
    merged_docs: list[Any]
    verify_top_k: int


class QueryDecomposeGraph:
    """쿼리 분해 그래프."""

    def __init__(
        self,
        llm_client: LlmClient | None = None,
        retriever: Any | None = None,
        max_sub_queries: int = 4,
        search_concurrency: int = 4,
        verify_top_k: int = 10,
    ) -> None:
        """그래프 의존성을 초기화한다.

        Args:
            llm_client: 분해 노드에서 사용할 LLM 클라이언트.
            retriever: 검색기(선택).
            max_sub_queries: 하위 질문 최대 개수.
            search_concurrency: 병렬 검색 동시성 제한.
            verify_top_k: 그룹별 검증 대상 상한.
        """
        self._retriever = retriever
        self._max_sub_queries = max(1, max_sub_queries)
        self._search_concurrency = max(1, search_concurrency)
        self._verify_top_k = max(1, verify_top_k)
        self._decompose_node = QueryDecomposeNode(llm_client=llm_client)
        self._search_node = AsyncSearchNode()
        self._merge_node = MergeNode()

    def build(self) -> Any:
        """그래프를 구성하고 컴파일된 객체를 반환한다."""
        graph = StateGraph(QueryDecomposeState)
        graph.add_node("decompose", self._node_decompose)
        graph.add_node("search", self._node_search)
        graph.add_node("verify", self._node_verify)
        graph.add_node("merge", self._node_merge)
        graph.set_entry_point("decompose")
        graph.add_edge("decompose", "search")
        graph.add_edge("search", "verify")
        graph.add_edge("verify", "merge")
        graph.add_edge("merge", END)
        return graph.compile()

    def run(self, question: str, retriever: Any | None = None) -> list[Any]:
        """쿼리 분해 그래프를 실행해 병합 결과를 반환한다."""
        app = self.build()
        result = app.invoke(
            {
                "question": question,
                "retriever": retriever if retriever is not None else self._retriever,
                "verify_top_k": self._verify_top_k,
            }
        )
        return result.get("merged_docs", [])

    def _node_decompose(self, state: QueryDecomposeState) -> QueryDecomposeState:
        """질문을 하위 쿼리로 분해한다."""
        question = state["question"]
        try:
            sub_queries = self._decompose_node.run(question)
        except NotImplementedError:
            sub_queries = self._fallback_decompose(question)
        except Exception:
            sub_queries = [question]
        normalized = self._normalize_queries(sub_queries, question)
        return {"sub_queries": normalized}

    def _node_search(self, state: QueryDecomposeState) -> QueryDecomposeState:
        """하위 쿼리를 병렬 검색한다.

        LangGraph `invoke` 경로에서 호출되므로 동기 함수로 유지한다.
        내부 비동기 노드는 `asyncio.run`으로 실행한다.
        """
        retriever = state.get("retriever")
        queries = state.get("sub_queries", [state["question"]])
        if retriever is None:
            return {"search_groups": [[] for _ in queries]}

        try:
            groups = self._run_async(self._search_node.run(queries, retriever))
            return {"search_groups": groups}
        except NotImplementedError:
            groups = self._fallback_search(queries, retriever)
            return {"search_groups": groups}
        except Exception:
            return {"search_groups": [[] for _ in queries]}

    def _node_verify(self, state: QueryDecomposeState) -> QueryDecomposeState:
        """검색 결과를 검증 기준으로 필터링한다."""
        question = state["question"]
        groups = state.get("search_groups", [])
        top_k = int(state.get("verify_top_k", self._verify_top_k))
        verified_groups: list[list[Any]] = []
        for group in groups:
            candidates = list(group)[:top_k]
            verified_groups.append(
                [doc for doc in candidates if self._is_relevant_doc(question=question, doc=doc)]
            )
        return {"verified_groups": verified_groups}

    def _node_merge(self, state: QueryDecomposeState) -> QueryDecomposeState:
        """검증된 검색 결과를 병합한다."""
        groups = state.get("verified_groups", [])
        try:
            merged = self._merge_node.run(groups)
        except NotImplementedError:
            merged = self._fallback_merge(groups)
        except Exception:
            merged = self._fallback_merge(groups)
        return {"merged_docs": merged}

    def _normalize_queries(self, queries: list[str], question: str) -> list[str]:
        """분해 결과를 정규화하고 개수 제한을 적용한다."""
        cleaned: list[str] = []
        for query in queries:
            text = query.strip()
            if text and text not in cleaned:
                cleaned.append(text)
        if not cleaned:
            cleaned = [question]
        return cleaned[: self._max_sub_queries]

    def _fallback_decompose(self, question: str) -> list[str]:
        """노드 미구현 시 사용할 단순 분해 로직."""
        fragments = re.split(r"\s*(?:그리고|또는|및|,|/| vs | VS | 비교)\s*", question)
        queries = [fragment.strip() for fragment in fragments if fragment.strip()]
        if len(queries) <= 1:
            return [question]
        return queries

    def _fallback_search(self, queries: list[str], retriever: Any) -> list[list[Any]]:
        """노드 미구현 시 사용할 병렬 검색 로직."""
        async def run_all() -> list[list[Any]]:
            semaphore = asyncio.Semaphore(self._search_concurrency)

            async def search_one(query: str) -> list[Any]:
                async with semaphore:
                    if hasattr(retriever, "ainvoke"):
                        result = retriever.ainvoke(query)
                        docs = await result if asyncio.iscoroutine(result) else result
                    elif hasattr(retriever, "invoke"):
                        docs = retriever.invoke(query)
                    else:
                        docs = []
                    if docs is None:
                        return []
                    if isinstance(docs, list):
                        return docs
                    return [docs]

            return await asyncio.gather(*[search_one(query) for query in queries])

        return self._run_async(run_all())

    def _run_async(self, coroutine: Any) -> Any:
        """동기 컨텍스트에서 코루틴을 안전하게 실행한다."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coroutine)

        result_box: dict[str, Any] = {}
        error_box: dict[str, Exception] = {}

        def runner() -> None:
            try:
                result_box["result"] = asyncio.run(coroutine)
            except Exception as error:  # pragma: no cover
                error_box["error"] = error

        thread = Thread(target=runner, daemon=True)
        thread.start()
        thread.join()

        if "error" in error_box:
            raise error_box["error"]
        return result_box.get("result")

    def _fallback_merge(self, groups: list[list[Any]]) -> list[Any]:
        """노드 미구현 시 사용할 병합/중복 제거 로직."""
        merged: list[Any] = []
        seen_keys: set[str] = set()
        for group in groups:
            for doc in group:
                key = self._doc_key(doc)
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                merged.append(doc)
        return merged

    def _doc_key(self, doc: Any) -> str:
        """문서 중복 제거를 위한 키를 생성한다."""
        if isinstance(doc, dict):
            source_id = doc.get("source_id") or doc.get("id")
            if source_id is not None:
                return str(source_id)
            content = doc.get("content") or doc.get("page_content")
            return str(content)
        metadata = getattr(doc, "metadata", None)
        if isinstance(metadata, dict):
            source_id = metadata.get("source_id") or metadata.get("id")
            if source_id is not None:
                return str(source_id)
        page_content = getattr(doc, "page_content", None)
        if page_content is not None:
            return str(page_content)
        return str(doc)

    def _is_relevant_doc(self, question: str, doc: Any) -> bool:
        """검색-검증-병합 패턴의 최소 검증 규칙을 적용한다."""
        text = self._doc_text(doc).lower()
        if text == "":
            return False
        question_tokens = [token for token in re.findall(r"[a-zA-Z0-9가-힣]+", question.lower()) if len(token) >= 2]
        if not question_tokens:
            return True
        return any(token in text for token in question_tokens)

    def _doc_text(self, doc: Any) -> str:
        """문서 객체에서 검증용 텍스트를 추출한다."""
        if isinstance(doc, str):
            return doc
        if isinstance(doc, dict):
            return str(doc.get("content") or doc.get("page_content") or "")
        return str(getattr(doc, "page_content", "") or str(doc))
