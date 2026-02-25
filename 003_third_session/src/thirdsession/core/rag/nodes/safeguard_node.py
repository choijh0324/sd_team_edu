# 목적: 입력 안전 검사를 수행한다.
# 설명: 질문을 안전 라벨로 분류한다.
# 디자인 패턴: Command
# 참조: thirdsession/core/rag/const/safeguard_label.py

"""입력 안전 검사 노드 모듈."""

from __future__ import annotations

import re

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from thirdsession.core.common.llm_client import LlmClient
from thirdsession.core.rag.const import SafeguardLabel


class SafeguardNode:
    """입력 안전 검사 노드."""

    def __init__(self, llm_client: LlmClient | None = None) -> None:
        """노드 의존성을 초기화한다.

        Args:
            llm_client: 안전 분류에 사용할 LLM 클라이언트(선택).
        """
        self._llm_client = llm_client
        self._prompt = PromptTemplate.from_template(
            (
                "너는 안전 분류기다. 아래 사용자 입력을 분류하라.\n"
                "반드시 PASS, PII, HARMFUL, PROMPT_INJECTION 중 하나만 출력한다.\n"
                "입력: {question}\n"
            )
        )

    def run(self, question: str) -> SafeguardLabel:
        """질문을 안전 라벨로 분류한다."""
        normalized_question = question.strip()
        if normalized_question == "":
            return SafeguardLabel.PASS

        # 1) 규칙 기반 1차 분류
        rule_based = self._classify_by_rules(normalized_question)
        if rule_based != SafeguardLabel.PASS:
            return rule_based

        # 2) LLM 보조 분류(주입된 경우에만 사용)
        if self._llm_client is not None:
            llm_label = self._classify_by_llm(normalized_question)
            if llm_label is not None:
                return llm_label

        return SafeguardLabel.PASS

    def _classify_by_rules(self, question: str) -> SafeguardLabel:
        """정규식/키워드 규칙으로 안전 라벨을 판정한다."""
        lowered = question.lower()

        pii_patterns = [
            r"\b\d{6}-\d{7}\b",  # 주민등록번호
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN 유사 패턴
            r"\b010-\d{4}-\d{4}\b",  # 휴대폰 번호
            r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",  # 이메일
            r"\b\d{16}\b",  # 카드번호 유사 패턴
        ]
        if any(re.search(pattern, question) for pattern in pii_patterns):
            return SafeguardLabel.PII

        harmful_keywords = [
            "폭탄",
            "총기",
            "마약",
            "자살",
            "해킹",
            "악성코드",
            "랜섬웨어",
            "피싱",
            "테러",
        ]
        if any(keyword in lowered for keyword in harmful_keywords):
            return SafeguardLabel.HARMFUL

        injection_keywords = [
            "ignore previous",
            "system prompt",
            "developer message",
            "jailbreak",
            "프롬프트 무시",
            "시스템 지시 무시",
            "규칙을 무시",
        ]
        if any(keyword in lowered for keyword in injection_keywords):
            return SafeguardLabel.PROMPT_INJECTION

        return SafeguardLabel.PASS

    def _classify_by_llm(self, question: str) -> SafeguardLabel | None:
        """LLM으로 안전 라벨을 보조 판정한다."""
        try:
            chain = self._prompt | self._llm_client.chat_model() | StrOutputParser()
            raw = chain.invoke({"question": question})
        except Exception:
            return None
        return self._parse_label(raw)

    def _parse_label(self, raw: str) -> SafeguardLabel:
        """LLM 출력 라벨을 enum으로 변환한다."""
        value = raw.strip().upper()
        if value == SafeguardLabel.PASS.value:
            return SafeguardLabel.PASS
        if value == SafeguardLabel.PII.value:
            return SafeguardLabel.PII
        if value == SafeguardLabel.HARMFUL.value:
            return SafeguardLabel.HARMFUL
        if value == SafeguardLabel.PROMPT_INJECTION.value:
            return SafeguardLabel.PROMPT_INJECTION
        return SafeguardLabel.PASS
