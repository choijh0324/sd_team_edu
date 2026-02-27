# 목적: 도구 실행 노드를 정의한다.
# 설명: 계획에 포함된 도구를 호출하고 결과를 저장한다.
# 디자인 패턴: 커맨드 패턴
# 참조: fourthsession/core/housing_agent/state

"""도구 실행 노드 모듈."""

from __future__ import annotations

import logging

from fourthsession.mcp.tool_registry import HousingToolRegistry
from fourthsession.core.housing_agent.state.agent_state import HousingAgentState


LOGGER = logging.getLogger(__name__)


class ExecuteNode:
    """도구 실행 노드."""

    def __init__(self, tool_registry: HousingToolRegistry | None = None) -> None:
        """실행 노드 의존성을 초기화한다.

        Args:
            tool_registry (HousingToolRegistry | None): 도구 레지스트리.
        """
        self._tool_registry = tool_registry

    def __call__(self, state: HousingAgentState) -> dict:
        """도구 실행 결과를 상태 업데이트로 반환한다.

        Args:
            state (HousingAgentState): 현재 상태.

        Returns:
            dict: 상태 업데이트 딕셔너리.
        """
        errors = list(state.errors or [])
        tool_results = list(state.tool_results or [])

        if not state.plan_valid:
            errors.append("계획 검증이 완료되지 않아 도구 실행을 건너뜁니다.")
            return {"tool_results": tool_results, "errors": errors}

        if not isinstance(state.plan, dict):
            errors.append("계획이 없어 도구 실행을 진행할 수 없습니다.")
            return {"tool_results": tool_results, "errors": errors}

        steps = state.plan.get("steps")
        if not isinstance(steps, list) or not steps:
            errors.append("실행할 step이 없습니다.")
            return {"tool_results": tool_results, "errors": errors}

        registry = self._tool_registry or HousingToolRegistry()
        try:
            registry.register_tools()
        except NotImplementedError:
            errors.append("도구 레지스트리가 미구현 상태입니다.")
            return {"tool_results": tool_results, "errors": errors}
        except Exception:
            LOGGER.exception("도구 레지스트리 초기화에 실패했습니다.")
            errors.append("도구 레지스트리 초기화에 실패했습니다.")
            return {"tool_results": tool_results, "errors": errors}

        for step in steps:
            if not isinstance(step, dict):
                errors.append("step 형식이 올바르지 않아 건너뜁니다.")
                continue

            step_id = str(step.get("id", "unknown"))
            tool_name = step.get("tool")
            payload = step.get("input", {})

            if not isinstance(tool_name, str) or not tool_name.strip():
                errors.append(f"{step_id}: tool 이름이 비어 있습니다.")
                continue
            if not isinstance(payload, dict):
                errors.append(f"{step_id}: input 형식이 올바르지 않습니다.")
                continue

            try:
                tool = registry.get_tool(tool_name)
            except NotImplementedError:
                errors.append(f"{step_id}: 도구 조회 로직이 미구현 상태입니다.")
                continue
            except Exception:
                LOGGER.exception("도구 조회에 실패했습니다: step_id=%s", step_id)
                errors.append(f"{step_id}: 도구 조회 중 예외가 발생했습니다.")
                continue

            if tool is None:
                errors.append(f"{step_id}: 등록되지 않은 도구입니다. tool={tool_name}")
                continue

            try:
                LOGGER.info(
                    "[agent][tool_call][start] trace_id=%s step_id=%s tool=%s input_keys=%s",
                    state.trace_id,
                    step_id,
                    tool_name,
                    sorted(payload.keys()),
                )
                result = tool.execute(payload)
                LOGGER.info(
                    "[agent][tool_call][end] trace_id=%s step_id=%s tool=%s result_keys=%s",
                    state.trace_id,
                    step_id,
                    tool_name,
                    sorted(result.keys()) if isinstance(result, dict) else [],
                )
                tool_results.append(
                    {
                        "step_id": step_id,
                        "tool": tool_name,
                        "input": payload,
                        "result": result if isinstance(result, dict) else {"value": result},
                    }
                )
            except NotImplementedError:
                errors.append(f"{step_id}: 도구 실행이 미구현 상태입니다. tool={tool_name}")
            except Exception:
                LOGGER.exception("도구 실행에 실패했습니다: step_id=%s, tool=%s", step_id, tool_name)
                errors.append(f"{step_id}: 도구 실행 중 예외가 발생했습니다. tool={tool_name}")

        return {"tool_results": tool_results, "errors": errors}
