# 목적: 결과 합성 노드를 정의한다.
# 설명: 여러 도구 결과를 하나의 응답 데이터로 합성한다.
# 디자인 패턴: 머저 패턴
# 참조: fourthsession/core/housing_agent/state

"""결과 합성 노드 모듈."""

from __future__ import annotations

import json

from fourthsession.core.housing_agent.state.agent_state import HousingAgentState


class MergeResultNode:
    """결과 합성 노드."""

    def __call__(self, state: HousingAgentState) -> dict:
        """합성 결과를 상태 업데이트로 반환한다.

        Args:
            state (HousingAgentState): 현재 상태.

        Returns:
            dict: 상태 업데이트 딕셔너리.
        """
        tool_results = list(state.tool_results or [])
        errors = list(state.errors or [])

        if not tool_results:
            if errors:
                return {
                    "answer": "요청을 처리했지만 도구 실행 결과가 없습니다. 오류를 확인해 주세요.",
                    "tool_results": tool_results,
                }
            return {
                "answer": "요청을 처리할 수 있는 도구 결과가 없습니다.",
                "tool_results": tool_results,
            }

        merged_sections: list[str] = []
        for index, result in enumerate(tool_results, start=1):
            if not isinstance(result, dict):
                merged_sections.append(f"{index}. 결과 형식이 올바르지 않습니다.")
                continue

            tool_name = result.get("tool", "unknown_tool")
            payload = result.get("result", {})
            if isinstance(payload, dict):
                rendered = json.dumps(payload, ensure_ascii=False)
            else:
                rendered = str(payload)
            merged_sections.append(f"{index}. {tool_name}: {rendered}")

        merged_answer = "도구 실행 결과 요약:\n" + "\n".join(merged_sections)
        return {
            "answer": merged_answer,
            "tool_results": tool_results,
        }
