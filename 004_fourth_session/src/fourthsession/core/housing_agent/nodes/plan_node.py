# 목적: 계획 생성 노드를 정의한다.
# 설명: 사용자 질문과 도구 목록을 바탕으로 실행 계획을 만든다.
# 디자인 패턴: 플래너 패턴
# 참조: fourthsession/core/housing_agent/state

"""계획 생성 노드 모듈."""

from __future__ import annotations

import json
import logging
import os

from langchain_google_genai import ChatGoogleGenerativeAI

from fourthsession.core.housing_agent.const.agent_constants import HousingAgentConstants
from fourthsession.core.housing_agent.prompts.agent_prompts import HousingAgentPrompts
from fourthsession.core.housing_agent.state.agent_state import HousingAgentState


LOGGER = logging.getLogger(__name__)


class PlanNode:
    """계획 생성 노드."""

    def __init__(self, model_name: str | None = None, temperature: float = 0.0) -> None:
        """계획 노드 의존성을 초기화한다.

        Args:
            model_name (str | None): 사용할 Gemini 모델명.
            temperature (float): 생성 온도.
        """
        self._constants = HousingAgentConstants()
        self._prompts = HousingAgentPrompts()
        self._model_name = model_name or os.getenv("LLM_MODEL", "gemini-2.0-flash")
        self._temperature = temperature

    def __call__(self, state: HousingAgentState) -> dict:
        """계획을 생성하고 상태 업데이트를 반환한다.

        Args:
            state (HousingAgentState): 현재 상태.

        Returns:
            dict: 상태 업데이트 딕셔너리.
        """
        question = state.question or ""
        tool_cards = state.tool_cards or []
        errors = list(state.errors or [])

        prompt = self._build_prompt(question=question, tool_cards=tool_cards)
        try:
            plan = self._generate_plan(prompt)
        except Exception:
            LOGGER.exception("계획 생성에 실패해 폴백 계획을 사용합니다.")
            errors.append("계획 생성 실패: 폴백 계획을 사용합니다.")
            plan = self._build_fallback_plan(tool_cards=tool_cards, question=question)

        return {"plan": plan, "errors": errors}

    def _generate_plan(self, prompt: str) -> dict:
        """LLM 호출로 계획 JSON을 생성한다."""
        if not os.getenv("GOOGLE_API_KEY"):
            raise ValueError("GOOGLE_API_KEY가 설정되지 않았습니다.")

        llm = ChatGoogleGenerativeAI(
            model=self._model_name,
            temperature=self._temperature,
        )
        response = llm.invoke(prompt)
        content = getattr(response, "content", response)
        if not isinstance(content, str):
            raise ValueError("LLM 응답이 문자열이 아닙니다.")
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ValueError("계획 JSON 루트가 객체가 아닙니다.")
        return parsed

    def _build_prompt(self, question: str, tool_cards: list[dict]) -> str:
        """질문/도구 카드를 포함한 계획 프롬프트를 만든다."""
        return (
            f"{self._prompts.plan_prompt()}\n\n"
            f"[사용자 질문]\n{question}\n\n"
            "[도구 카드 목록(JSON)]\n"
            f"{json.dumps(tool_cards, ensure_ascii=False)}"
        )

    def _build_fallback_plan(self, tool_cards: list[dict], question: str) -> dict:
        """LLM 실패 시 사용할 기본 계획을 생성한다."""
        selected_tool = self._select_tool_name(tool_cards)
        return {
            "version": self._constants.plan_version,
            "goal": "주택 질문에 맞는 데이터 조회 및 요약",
            "steps": [
                {
                    "id": "step-1",
                    "action": self._constants.plan_action_name,
                    "tool": selected_tool,
                    "input": {"question": question, "limit": self._constants.default_list_limit},
                }
            ],
        }

    def _select_tool_name(self, tool_cards: list[dict]) -> str:
        """도구 카드에서 기본 도구 이름을 선택한다."""
        for card in tool_cards:
            if isinstance(card, dict):
                name = card.get("name")
                if isinstance(name, str) and name.strip():
                    return name.strip()
        return "housing_price_stats_tool"
