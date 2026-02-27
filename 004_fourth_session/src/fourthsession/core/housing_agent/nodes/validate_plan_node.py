# 목적: 계획 검증 노드를 정의한다.
# 설명: 계획 스키마와 도구 일치 여부를 확인한다.
# 디자인 패턴: 밸리데이터 패턴
# 참조: fourthsession/core/housing_agent/state

"""계획 검증 노드 모듈."""

from __future__ import annotations

from fourthsession.core.housing_agent.const.agent_constants import HousingAgentConstants
from fourthsession.core.housing_agent.state.agent_state import HousingAgentState


class ValidatePlanNode:
    """계획 검증 노드."""

    def __init__(self) -> None:
        """검증 노드 의존성을 초기화한다."""
        self._constants = HousingAgentConstants()

    def __call__(self, state: HousingAgentState) -> dict:
        """계획 검증 결과를 상태 업데이트로 반환한다.

        Args:
            state (HousingAgentState): 현재 상태.

        Returns:
            dict: 상태 업데이트 딕셔너리.
        """
        plan = state.plan
        errors = list(state.errors or [])
        retry_count = state.retry_count

        if not isinstance(plan, dict):
            errors.append("계획 형식이 올바르지 않습니다.")
            return {"plan_valid": False, "errors": errors, "retry_count": retry_count + 1}

        if plan.get("version") != self._constants.plan_version:
            errors.append(
                f"계획 버전이 일치하지 않습니다. expected={self._constants.plan_version}"
            )

        goal = plan.get("goal")
        if not isinstance(goal, str) or not goal.strip():
            errors.append("계획 goal은 비어 있지 않은 문자열이어야 합니다.")

        steps = plan.get("steps")
        if not isinstance(steps, list) or not steps:
            errors.append("계획 steps는 1개 이상의 리스트여야 합니다.")
            return {"plan_valid": False, "errors": errors, "retry_count": retry_count + 1}

        available_tools = self._extract_tool_names(state.tool_cards)
        step_ids: set[str] = set()

        for step in steps:
            if not isinstance(step, dict):
                errors.append("각 step은 객체여야 합니다.")
                continue

            step_id = step.get("id")
            if not isinstance(step_id, str) or not step_id.strip():
                errors.append("step.id는 비어 있지 않은 문자열이어야 합니다.")
            elif step_id in step_ids:
                errors.append(f"중복된 step.id가 존재합니다: {step_id}")
            else:
                step_ids.add(step_id)

            action = step.get("action")
            if action != self._constants.plan_action_name:
                errors.append(
                    f"지원하지 않는 action입니다: {action}. "
                    f"허용값={self._constants.plan_action_name}"
                )

            tool = step.get("tool")
            if not isinstance(tool, str) or not tool.strip():
                errors.append("step.tool은 비어 있지 않은 문자열이어야 합니다.")
            elif available_tools and tool not in available_tools:
                errors.append(f"등록되지 않은 도구입니다: {tool}")

            step_input = step.get("input")
            if not isinstance(step_input, dict):
                errors.append("step.input은 객체여야 합니다.")

        is_valid = len(errors) == len(state.errors or [])
        updates = {"plan_valid": is_valid, "errors": errors}
        if not is_valid:
            updates["retry_count"] = retry_count + 1
        return updates

    def _extract_tool_names(self, tool_cards: list[dict]) -> set[str]:
        """도구 카드 목록에서 도구 이름 집합을 추출한다."""
        tool_names: set[str] = set()
        for card in tool_cards or []:
            if not isinstance(card, dict):
                continue
            name = card.get("name")
            if isinstance(name, str) and name.strip():
                tool_names.add(name.strip())
        return tool_names
