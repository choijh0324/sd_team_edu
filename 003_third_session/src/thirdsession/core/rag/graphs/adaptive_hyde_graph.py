# 목적: 적응형 HyDE 그래프를 정의한다.
# 설명: 기본 검색 결과가 부족하면 HyDE를 수행하는 흐름이다.
# 디자인 패턴: State Machine
# 참조: thirdsession/core/rag/nodes/hyde_node.py

"""적응형 HyDE 그래프 모듈."""

from __future__ import annotations

import asyncio
import re
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from thirdsession.core.common.llm_client import LlmClient
from thirdsession.core.rag.nodes.hyde_node import HydeNode
from thirdsession.core.rag.nodes.merge_node import MergeNode


class AdaptiveHydeState(TypedDict, total=False):
    """적응형 HyDE 그래프 상태."""

    question: str
    store: Any
    base_docs: list[Any]
    hyde_docs: list[Any]
    merged_docs: list[Any]
    style_hint: str
    use_hyde: bool
    base_k: int
    hyde_k: int


class AdaptiveHydeGraph:
    """적응형 HyDE 그래프."""

    def __init__(
        self,
        llm_client: LlmClient | None = None,
        store: Any | None = None,
        base_k: int = 3,
        hyde_k: int = 3,
    ) -> None:
        """그래프 의존성을 초기화한다.

        Args:
            llm_client: HyDE 노드에서 사용할 LLM 클라이언트.
            store: 벡터 스토어(선택).
            base_k: 기본 검색 개수.
            hyde_k: HyDE 재검색 개수.
        """
        self._store = store
        self._base_k = max(1, base_k)
        self._hyde_k = max(1, hyde_k)
        self._hyde_node = HydeNode(llm_client=llm_client)
        self._merge_node = MergeNode()

    def build(self) -> Any:
        """그래프를 구성하고 컴파일된 객체를 반환한다."""
        graph = StateGraph(AdaptiveHydeState)
        graph.add_node("search", self._node_search)
        graph.add_node("judge", self._node_judge)
        graph.add_node("hyde", self._node_hyde)
        graph.add_node("merge", self._node_merge)
        graph.set_entry_point("search")
        graph.add_edge("search", "judge")
        graph.add_conditional_edges(
            "judge",
            lambda state: state.get("use_hyde", False),
            {True: "hyde", False: "merge"},
        )
        graph.add_edge("hyde", "merge")
        graph.add_edge("merge", END)
        return graph.compile()

    def run(self, question: str, store: Any | None = None) -> list[Any]:
        """적응형 HyDE 그래프를 실행해 병합 결과를 반환한다."""
        app = self.build()
        result = app.invoke(
            {
                "question": question,
                "store": store if store is not None else self._store,
                "base_k": self._base_k,
                "hyde_k": self._hyde_k,
            }
        )
        return result.get("merged_docs", [])

    def _node_search(self, state: AdaptiveHydeState) -> AdaptiveHydeState:
        """기본 검색을 수행한다."""
        question = state["question"]
        store = state.get("store")
        base_k = int(state.get("base_k", self._base_k))
        if store is None:
            return {"base_docs": [], "style_hint": "일반 가이드 문서 형식"}

        base_docs = self._search_docs(question=question, store=store, k=base_k)
        style_hint = self._extract_style_hint(base_docs)
        return {
            "base_docs": base_docs,
            "style_hint": style_hint,
        }

    def _node_judge(self, state: AdaptiveHydeState) -> AdaptiveHydeState:
        """기본 검색 결과의 충분성을 판단해 HyDE 적용 여부를 결정한다."""
        question = state["question"]
        base_docs = state.get("base_docs", [])
        use_hyde = self._should_use_hyde(question=question, docs=base_docs)
        return {"use_hyde": use_hyde}

    def _node_hyde(self, state: AdaptiveHydeState) -> AdaptiveHydeState:
        """HyDE 기반 재검색을 수행한다."""
        question = state["question"]
        store = state.get("store")
        if store is None:
            return {"hyde_docs": []}

        try:
            hyde_docs = self._hyde_node.run(question=question, store=store)
            return {"hyde_docs": list(hyde_docs) if hyde_docs is not None else []}
        except NotImplementedError:
            # HyDE 노드 미구현 시 질문 확장 검색으로 폴백한다.
            hyde_docs = self._fallback_hyde_search(
                question=question,
                style_hint=state.get("style_hint", "일반 가이드 문서 형식"),
                store=store,
                k=int(state.get("hyde_k", self._hyde_k)),
            )
            return {"hyde_docs": hyde_docs}
        except Exception:
            return {"hyde_docs": []}

    def _node_merge(self, state: AdaptiveHydeState) -> AdaptiveHydeState:
        """기본 검색 결과와 HyDE 검색 결과를 병합한다."""
        groups = [state.get("base_docs", []), state.get("hyde_docs", [])]
        try:
            merged_docs = self._merge_node.run(groups)
        except NotImplementedError:
            merged_docs = self._fallback_merge(groups)
        except Exception:
            merged_docs = self._fallback_merge(groups)
        return {"merged_docs": merged_docs}

    def _search_docs(self, question: str, store: Any, k: int) -> list[Any]:
        """벡터 스토어 인터페이스에 맞춰 기본 검색을 수행한다."""
        if hasattr(store, "similarity_search"):
            docs = store.similarity_search(question, k=k)
            if docs is None:
                return []
            return docs if isinstance(docs, list) else [docs]
        if hasattr(store, "ainvoke"):
            result = asyncio.run(self._run_ainvoke(store, question))
            if result is None:
                return []
            return result if isinstance(result, list) else [result]
        if hasattr(store, "invoke"):
            docs = store.invoke(question)
            if docs is None:
                return []
            return docs if isinstance(docs, list) else [docs]
        return []

    async def _run_ainvoke(self, store: Any, question: str) -> Any:
        """ainvoke 검색을 보조 실행한다."""
        return await store.ainvoke(question)

    def _should_use_hyde(self, question: str, docs: list[Any]) -> bool:
        """검색 결과가 불충분하면 HyDE 전환을 결정한다."""
        if len(docs) == 0:
            return True
        question_tokens = [token for token in re.findall(r"[a-zA-Z0-9가-힣]+", question.lower()) if len(token) >= 2]
        if not question_tokens:
            return False
        hit_count = 0
        for doc in docs:
            text = self._doc_text(doc).lower()
            if any(token in text for token in question_tokens):
                hit_count += 1
        # 기본 검색 문서의 절반 미만만 관련되면 HyDE를 활성화한다.
        return hit_count < max(1, len(docs) // 2)

    def _extract_style_hint(self, docs: list[Any]) -> str:
        """기존 문서에서 HyDE 스타일 힌트를 추출한다."""
        if not docs:
            return "일반 가이드 문서 형식"
        first = docs[0]
        raw_text = self._doc_text(first)
        one_line = " ".join(raw_text.split())
        trimmed = one_line[:300]
        return trimmed if trimmed else "일반 가이드 문서 형식"

    def _fallback_hyde_search(self, question: str, style_hint: str, store: Any, k: int) -> list[Any]:
        """HyDE 노드 미구현 시 질문+스타일 힌트로 재검색한다."""
        hyde_like_query = f"{question}\n문서 형식 힌트: {style_hint}"
        return self._search_docs(question=hyde_like_query, store=store, k=k)

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
            return str(doc.get("content") or doc.get("page_content") or doc)
        metadata = getattr(doc, "metadata", None)
        if isinstance(metadata, dict):
            source_id = metadata.get("source_id") or metadata.get("id")
            if source_id is not None:
                return str(source_id)
        page_content = getattr(doc, "page_content", None)
        if page_content is not None:
            return str(page_content)
        return str(doc)

    def _doc_text(self, doc: Any) -> str:
        """문서 객체에서 텍스트를 추출한다."""
        if isinstance(doc, str):
            return doc
        if isinstance(doc, dict):
            return str(doc.get("content") or doc.get("page_content") or "")
        return str(getattr(doc, "page_content", "") or str(doc))
