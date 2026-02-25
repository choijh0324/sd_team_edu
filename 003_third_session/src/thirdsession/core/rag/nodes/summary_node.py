# 목적: 대화 요약을 생성한다.
# 설명: 누적된 history를 요약해 summary를 갱신한다.
# 디자인 패턴: Command
# 참조: nextStep.md

"""대화 요약 노드 모듈."""

from __future__ import annotations

from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from thirdsession.core.common.llm_client import LlmClient


class SummaryNode:
    """대화 요약 노드."""

    def __init__(
        self,
        llm_client: LlmClient | None = None,
        max_history_items: int = 12,
        max_output_chars: int = 600,
    ) -> None:
        """요약 노드 의존성과 정책을 초기화한다.

        Args:
            llm_client: 요약 생성에 사용할 LLM 클라이언트(선택).
            max_history_items: 요약에 반영할 최대 대화 턴 수.
            max_output_chars: 최종 요약 최대 길이.
        """
        self._llm_client = llm_client
        self._max_history_items = max(1, max_history_items)
        self._max_output_chars = max(100, max_output_chars)
        self._summary_prompt = PromptTemplate.from_template(
            (
                "다음 대화 이력을 3~5문장으로 요약하라.\n"
                "중요한 사용자 요구사항과 제약조건을 우선 포함하라.\n"
                "추측은 금지하며, 대화에 나온 정보만 사용하라.\n\n"
                "[기존 요약]\n{previous_summary}\n\n"
                "[대화 이력]\n{history_text}\n"
            )
        )

    def run(self, history: list[dict[str, Any]], previous_summary: str | None) -> str:
        """대화 요약을 생성한다."""
        if not history:
            return (previous_summary or "").strip()

        history_text = self._format_history(history[-self._max_history_items :])
        safe_previous_summary = (previous_summary or "").strip()

        if self._llm_client is None:
            return self._fallback_summary(history_text, safe_previous_summary)

        try:
            chain = self._summary_prompt | self._llm_client.chat_model() | StrOutputParser()
            output = chain.invoke(
                {
                    "previous_summary": safe_previous_summary or "(없음)",
                    "history_text": history_text,
                }
            )
            return self._normalize_summary(output, safe_previous_summary)
        except Exception:
            return self._fallback_summary(history_text, safe_previous_summary)

    def _format_history(self, history: list[dict[str, Any]]) -> str:
        """대화 이력을 요약 입력 문자열로 변환한다."""
        lines: list[str] = []
        for index, item in enumerate(history, start=1):
            role = str(item.get("role") or item.get("type") or "unknown").strip()
            content = str(item.get("content") or item.get("message") or "").strip()
            if content == "":
                continue
            compact = " ".join(content.split())
            lines.append(f"{index}. {role}: {compact}")
        return "\n".join(lines)

    def _fallback_summary(self, history_text: str, previous_summary: str) -> str:
        """LLM 미사용/실패 시 규칙 기반 요약을 생성한다."""
        if history_text.strip() == "":
            return previous_summary
        lines = [line.strip() for line in history_text.splitlines() if line.strip()]
        picked = lines[-5:]
        base = " / ".join(picked)
        if previous_summary:
            merged = f"{previous_summary} | 최근 대화: {base}"
        else:
            merged = f"최근 대화 요약: {base}"
        return self._normalize_summary(merged, previous_summary)

    def _normalize_summary(self, summary: str, previous_summary: str) -> str:
        """요약 문자열을 정리하고 길이를 제한한다."""
        compact = " ".join(summary.split())
        if compact == "":
            return previous_summary
        return compact[: self._max_output_chars]
