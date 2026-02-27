# 목적: 주택 에이전트 서비스 레이어를 정의한다.
# 설명: 요청을 받아 에이전트 실행을 조정하고 응답을 만든다.
# 디자인 패턴: 애플리케이션 서비스 패턴
# 참조: fourthsession/core/housing_agent/graph

"""주택 에이전트 서비스 모듈."""

from __future__ import annotations

import logging
from typing import Any

from fourthsession.api.housing_agent.model.request import HousingAgentRequest
from fourthsession.api.housing_agent.model.response import HousingAgentResponse
from fourthsession.core.housing_agent.graph.graph_builder import HousingAgentGraphBuilder
from fourthsession.core.housing_agent.state.agent_state import HousingAgentState
from fourthsession.mcp.tool_registry import HousingToolRegistry


LOGGER = logging.getLogger(__name__)


class HousingAgentService:
    """주택 에이전트 서비스."""

    def __init__(
        self,
        tool_registry: HousingToolRegistry | None = None,
        graph_builder: HousingAgentGraphBuilder | None = None,
    ) -> None:
        """서비스 의존성을 초기화한다.

        Args:
            tool_registry (HousingToolRegistry | None): 도구 레지스트리.
            graph_builder (HousingAgentGraphBuilder | None): 그래프 빌더.
        """
        self._tool_registry = tool_registry
        self._graph_builder = graph_builder

    def handle(self, request: HousingAgentRequest) -> HousingAgentResponse:
        """요청을 처리하고 응답을 반환한다.

        Args:
            request (HousingAgentRequest): 요청 모델.

        Returns:
            HousingAgentResponse: 응답 모델.
        """
        errors: list[str] = []
        tool_cards: list[dict[str, Any]] = []

        registry = self._tool_registry or HousingToolRegistry()
        try:
            registry.register_tools()
            tool_cards = registry.list_tool_cards()
        except NotImplementedError:
            errors.append("ToolRegistry가 아직 구현되지 않아 기본 경로로 처리했습니다.")
        except Exception:
            errors.append("ToolRegistry 처리 중 예외가 발생했습니다.")
            LOGGER.exception("ToolRegistry 처리 실패")

        initial_state = {
            "question": request.question,
            "plan": None,
            "tool_results": [],
            "answer": None,
            "errors": [],
            "trace_id": request.trace_id,
            "plan_valid": False,
            "retry_count": 0,
            "max_retries": request.max_steps if request.max_steps is not None else 2,
            "tool_cards": tool_cards,
            "finalized": False,
        }

        result_dict: dict[str, Any] = initial_state
        builder = self._graph_builder or HousingAgentGraphBuilder()
        try:
            graph = builder.build()
            executable = graph.compile() if hasattr(graph, "compile") else graph
            if hasattr(executable, "invoke"):
                invoked = executable.invoke(initial_state)
            elif callable(executable):
                invoked = executable(initial_state)
            else:
                invoked = initial_state
                errors.append("그래프 실행 객체가 invoke/callable 형태가 아닙니다.")

            if isinstance(invoked, HousingAgentState):
                result_dict = invoked.model_dump()
            elif isinstance(invoked, dict):
                result_dict = invoked
            else:
                result_dict = initial_state
                errors.append("그래프 실행 결과 타입이 올바르지 않습니다.")
        except NotImplementedError:
            errors.append("그래프가 아직 구현되지 않아 기본 응답을 반환합니다.")
        except Exception:
            errors.append("그래프 실행 중 예외가 발생했습니다.")
            LOGGER.exception("그래프 실행 실패")

        answer = result_dict.get("answer")
        if not isinstance(answer, str) or not answer.strip():
            answer = "현재 에이전트 실행 경로가 준비되지 않아 기본 응답을 반환합니다."

        state_errors = result_dict.get("errors")
        merged_errors = list(errors)
        if isinstance(state_errors, list):
            merged_errors.extend(str(item) for item in state_errors if item is not None)

        response_payload = {
            "answer": answer,
            "trace_id": result_dict.get("trace_id") or request.trace_id,
            "metadata": {
                "tool_results": result_dict.get("tool_results", []),
                "errors": merged_errors,
                "plan": result_dict.get("plan"),
            },
        }
        return HousingAgentResponse.from_result(response_payload)
