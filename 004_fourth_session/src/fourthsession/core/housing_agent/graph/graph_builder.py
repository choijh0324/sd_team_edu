# 목적: 주택 에이전트 그래프를 구성한다.
# 설명: LangGraph의 StateGraph를 빌드하는 책임을 가진다.
# 디자인 패턴: 빌더 패턴
# 참조: fourthsession/core/housing_agent/nodes, fourthsession/core/housing_agent/state

"""주택 에이전트 그래프 빌더 모듈."""

from __future__ import annotations

import logging
from typing import Any, Callable

from langgraph.graph import END, StateGraph

from fourthsession.core.housing_agent.nodes.answer_node import AnswerNode
from fourthsession.core.housing_agent.nodes.execute_node import ExecuteNode
from fourthsession.core.housing_agent.nodes.feedback_node import FeedbackLoopNode
from fourthsession.core.housing_agent.nodes.merge_node import MergeResultNode
from fourthsession.core.housing_agent.nodes.plan_node import PlanNode
from fourthsession.core.housing_agent.nodes.validate_plan_node import ValidatePlanNode
from fourthsession.core.housing_agent.state.agent_state import HousingAgentState


LOGGER = logging.getLogger(__name__)


class HousingAgentGraphBuilder:
    """주택 에이전트 그래프 빌더."""

    def build(self) -> StateGraph:
        """그래프를 구성해 반환한다.

        Returns:
            StateGraph: 구성된 LangGraph 그래프.
        """
        graph = StateGraph(HousingAgentState)

        graph.add_node("plan", self._wrap_node("plan", PlanNode()))
        graph.add_node("validate", self._wrap_node("validate", ValidatePlanNode()))
        graph.add_node("execute", self._wrap_node("execute", ExecuteNode()))
        graph.add_node("merge", self._wrap_node("merge", MergeResultNode()))
        graph.add_node("feedback", self._wrap_node("feedback", FeedbackLoopNode()))
        graph.add_node("answer", self._wrap_node("answer", AnswerNode()))

        graph.set_entry_point("plan")
        graph.add_edge("plan", "validate")
        graph.add_edge("validate", "execute")
        graph.add_edge("execute", "merge")
        graph.add_edge("merge", "feedback")
        graph.add_conditional_edges(
            "feedback",
            self._route_after_feedback,
            {
                "plan": "plan",
                "answer": "answer",
            },
        )
        graph.add_edge("answer", END)
        return graph

    def _route_after_feedback(self, state: HousingAgentState | dict) -> str:
        """피드백 결과에 따라 다음 노드를 선택한다."""
        finalized = state.get("finalized") if isinstance(state, dict) else state.finalized
        route = "answer" if bool(finalized) else "plan"
        snapshot = self._state_snapshot(state)
        LOGGER.info("[graph][route] feedback -> %s | state=%s", route, snapshot)
        return route

    def _wrap_node(self, node_name: str, node: Callable[[HousingAgentState], dict]):
        """노드 실행 전후 상태를 로깅하는 래퍼를 생성한다."""

        def _wrapped(state: HousingAgentState | dict) -> dict:
            LOGGER.info(
                "[graph][enter] node=%s | state=%s",
                node_name,
                self._state_snapshot(state),
            )
            updates = node(state)  # type: ignore[arg-type]
            LOGGER.info(
                "[graph][exit] node=%s | updates=%s",
                node_name,
                self._updates_snapshot(updates),
            )
            return updates

        return _wrapped

    def _state_snapshot(self, state: HousingAgentState | dict) -> dict[str, Any]:
        """로그 출력을 위한 핵심 상태 요약을 만든다."""
        state_dict = state if isinstance(state, dict) else state.model_dump()
        return {
            "trace_id": state_dict.get("trace_id"),
            "retry_count": state_dict.get("retry_count"),
            "max_retries": state_dict.get("max_retries"),
            "plan_valid": state_dict.get("plan_valid"),
            "finalized": state_dict.get("finalized"),
            "errors": len(state_dict.get("errors", []) or []),
            "tool_results": len(state_dict.get("tool_results", []) or []),
        }

    def _updates_snapshot(self, updates: dict | Any) -> dict[str, Any]:
        """로그 출력을 위한 상태 업데이트 요약을 만든다."""
        if not isinstance(updates, dict):
            return {"type": type(updates).__name__}
        return {
            "keys": sorted(updates.keys()),
            "plan_valid": updates.get("plan_valid"),
            "finalized": updates.get("finalized"),
            "retry_count": updates.get("retry_count"),
            "errors": len(updates.get("errors", []) or []) if "errors" in updates else None,
            "tool_results": (
                len(updates.get("tool_results", []) or [])
                if "tool_results" in updates
                else None
            ),
            "answer_len": len(updates.get("answer", "")) if isinstance(updates.get("answer"), str) else None,
        }
