# 목적: 최종 답변 생성 노드를 정의한다.
# 설명: 합성된 도구 결과를 사용자 친화적 최종 답변으로 정리한다.
# 디자인 패턴: 커맨드 패턴
# 참조: fourthsession/core/housing_agent/prompts/agent_prompts.py

"""최종 답변 생성 노드 모듈."""

from __future__ import annotations

import json
import os

from langchain_google_genai import ChatGoogleGenerativeAI

from fourthsession.core.housing_agent.prompts.agent_prompts import HousingAgentPrompts
from fourthsession.core.housing_agent.state.agent_state import HousingAgentState


class AnswerNode:
    """최종 답변 생성 노드."""

    def __init__(self, model_name: str | None = None, temperature: float = 0.2) -> None:
        """답변 노드 의존성을 초기화한다.

        Args:
            model_name (str | None): 사용할 Gemini 모델명.
            temperature (float): 생성 온도.
        """
        self._prompts = HousingAgentPrompts()
        self._model_name = model_name or os.getenv("LLM_MODEL", "gemini-2.0-flash")
        self._temperature = temperature

    def __call__(self, state: HousingAgentState) -> dict:
        """최종 답변을 생성해 상태 업데이트를 반환한다.

        Args:
            state (HousingAgentState): 현재 상태.

        Returns:
            dict: 상태 업데이트 딕셔너리.
        """
        draft_answer = state.answer or ""
        if not draft_answer.strip():
            draft_answer = "요청 처리 결과가 충분하지 않아 기본 답변을 반환합니다."

        if not os.getenv("GOOGLE_API_KEY"):
            return {"answer": draft_answer, "finalized": True}

        prompt = self._build_prompt(
            question=state.question or "",
            draft_answer=draft_answer,
            tool_results=state.tool_results or [],
            errors=state.errors or [],
        )
        try:
            llm = ChatGoogleGenerativeAI(
                model=self._model_name,
                temperature=self._temperature,
            )
            response = llm.invoke(prompt)
            content = getattr(response, "content", response)
            if isinstance(content, str) and content.strip():
                return {"answer": content.strip(), "finalized": True}
        except Exception:
            return {"answer": draft_answer, "finalized": True}

        return {"answer": draft_answer, "finalized": True}

    def _build_prompt(
        self,
        question: str,
        draft_answer: str,
        tool_results: list[dict],
        errors: list[str],
    ) -> str:
        """최종 답변 생성을 위한 프롬프트를 구성한다."""
        return (
            f"{self._prompts.answer_prompt()}\n\n"
            f"[사용자 질문]\n{question}\n\n"
            f"[초안 답변]\n{draft_answer}\n\n"
            "[도구 실행 결과(JSON)]\n"
            f"{json.dumps(tool_results, ensure_ascii=False)}\n\n"
            "[오류 목록(JSON)]\n"
            f"{json.dumps(errors, ensure_ascii=False)}"
        )
