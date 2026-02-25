# 목적: HyDE 기반 재검색을 수행한다.
# 설명: 가상 문서를 생성해 재검색하는 노드이다.
# 디자인 패턴: Command
# 참조: thirdsession/core/rag/prompts/hyde_prompt.py

"""HyDE 노드 모듈."""

from __future__ import annotations

from typing import Any

from langchain_core.output_parsers import StrOutputParser

from thirdsession.core.common.llm_client import LlmClient
from thirdsession.core.rag.prompts.hyde_prompt import HYDE_PROMPT


class HydeNode:
    """HyDE 노드."""

    def __init__(
        self,
        llm_client: LlmClient | None = None,
        hyde_k: int = 3,
        max_hypothetical_chars: int = 1200,
    ) -> None:
        """노드 의존성을 초기화한다.

        Args:
            llm_client: LLM 클라이언트(선택).
            hyde_k: HyDE 재검색 문서 수.
            max_hypothetical_chars: 가상 문서 최대 길이.
        """
        self._llm_client = llm_client
        self._hyde_k = max(1, hyde_k)
        self._max_hypothetical_chars = max(200, max_hypothetical_chars)

    def run(self, question: str, store: Any) -> list[Any]:
        """가상 문서로 재검색한다.

        구현 내용:
            - LLM이 있으면 HyDE 프롬프트로 가상 문서를 생성한다.
            - 생성 실패/미설정 시 원 질문을 폴백 쿼리로 사용한다.
            - store 인터페이스에 맞춰 similarity_search 계열 검색을 수행한다.
        """
        normalized_question = question.strip()
        if normalized_question == "" or store is None:
            return []

        hypothetical_doc = self._generate_hypothetical_doc(normalized_question)
        query_for_search = hypothetical_doc if hypothetical_doc else normalized_question
        docs = self._search(store=store, query=query_for_search, k=self._hyde_k)
        return docs

    def _generate_hypothetical_doc(self, question: str) -> str:
        """질문 기반 가상 문서를 생성한다."""
        if self._llm_client is None:
            return ""
        try:
            chain = HYDE_PROMPT | self._llm_client.chat_model() | StrOutputParser()
            output = chain.invoke({"question": question})
            cleaned = " ".join(output.split())
            if cleaned == "":
                return ""
            return cleaned[: self._max_hypothetical_chars]
        except Exception:
            # HyDE 생성 실패 시 검색 폴백을 위해 빈 문자열을 반환한다.
            return ""

    def _search(self, store: Any, query: str, k: int) -> list[Any]:
        """스토어 인터페이스를 감지해 검색한다."""
        if hasattr(store, "similarity_search"):
            docs = store.similarity_search(query, k=k)
            return self._to_list(docs)

        if hasattr(store, "invoke"):
            docs = store.invoke(query)
            return self._to_list(docs)[:k]

        if hasattr(store, "ainvoke"):
            # 동기 run 컨텍스트이므로 비동기 인터페이스는 사용하지 않는다.
            return []

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
