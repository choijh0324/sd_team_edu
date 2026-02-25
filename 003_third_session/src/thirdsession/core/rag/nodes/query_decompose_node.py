# 목적: 질문을 하위 쿼리로 분해한다.
# 설명: 쿼리 분해 프롬프트를 이용하는 노드이다.
# 디자인 패턴: Command
# 참조: thirdsession/core/rag/prompts/query_decompose_prompt.py

"""쿼리 분해 노드 모듈."""

from __future__ import annotations

import re

from langchain_core.output_parsers import StrOutputParser

from thirdsession.core.common.llm_client import LlmClient
from thirdsession.core.rag.prompts.query_decompose_prompt import QUERY_DECOMPOSE_PROMPT


class QueryDecomposeNode:
    """쿼리 분해 노드."""

    def __init__(self, llm_client: LlmClient | None = None, max_sub_queries: int = 4) -> None:
        """노드 의존성을 초기화한다.

        Args:
            llm_client: LLM 클라이언트(선택).
            max_sub_queries: 최대 하위 질문 개수.
        """
        self._llm_client = llm_client
        self._max_sub_queries = max(1, max_sub_queries)

    def run(self, question: str) -> list[str]:
        """질문을 하위 쿼리로 분해한다.

        구현 내용:
            - LLM이 있으면 프롬프트 기반 분해를 시도한다.
            - LLM 미구현/실패 시 규칙 기반 분해로 폴백한다.
            - 결과는 중복 제거 후 최대 개수 제한을 적용한다.
        """
        normalized_question = question.strip()
        if normalized_question == "":
            return []

        if self._llm_client is None:
            return self._fallback_decompose(normalized_question)

        try:
            chain = QUERY_DECOMPOSE_PROMPT | self._llm_client.chat_model() | StrOutputParser()
            raw_output = chain.invoke({"question": normalized_question})
            parsed = self._parse_output(raw_output)
            if parsed:
                return parsed
        except Exception:
            # LLM 호출 실패 시에도 파이프라인이 중단되지 않도록 폴백한다.
            pass
        return self._fallback_decompose(normalized_question)

    def _parse_output(self, output: str) -> list[str]:
        """LLM 출력 텍스트를 하위 질문 리스트로 파싱한다."""
        candidates: list[str] = []
        for raw_line in output.splitlines():
            line = raw_line.strip()
            if line == "":
                continue
            # 번호/불릿/체크박스 제거
            line = re.sub(r"^[-*•\d\.\)\]\s]+", "", line).strip()
            line = re.sub(r"^\[[xX ]\]\s*", "", line).strip()
            if line == "":
                continue
            candidates.append(line)
        return self._normalize_queries(candidates)

    def _fallback_decompose(self, question: str) -> list[str]:
        """규칙 기반 하위 질문 분해를 수행한다."""
        fragments = re.split(r"\s*(?:그리고|또는|및|,|/| vs | VS | 비교|차이)\s*", question)
        candidates = [fragment.strip() for fragment in fragments if fragment.strip()]
        if not candidates:
            return [question]
        if len(candidates) == 1:
            return [question]
        return self._normalize_queries(candidates)

    def _normalize_queries(self, queries: list[str]) -> list[str]:
        """분해 결과를 정규화하고 최대 개수를 제한한다."""
        normalized: list[str] = []
        for query in queries:
            text = " ".join(query.split())
            if text == "":
                continue
            if text in normalized:
                continue
            normalized.append(text)
            if len(normalized) >= self._max_sub_queries:
                break
        return normalized
