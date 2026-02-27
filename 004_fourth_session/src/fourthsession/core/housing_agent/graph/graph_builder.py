# 목적: 주택 에이전트 그래프를 구성한다.
# 설명: LangGraph의 StateGraph를 빌드하는 책임을 가진다.
# 디자인 패턴: 빌더 패턴
# 참조: fourthsession/core/housing_agent/nodes, fourthsession/core/housing_agent/state

"""주택 에이전트 그래프 빌더 모듈."""

from langgraph.graph import END, StateGraph

from fourthsession.core.housing_agent.nodes.answer_node import AnswerNode
from fourthsession.core.housing_agent.nodes.execute_node import ExecuteNode
from fourthsession.core.housing_agent.nodes.feedback_node import FeedbackLoopNode
from fourthsession.core.housing_agent.nodes.merge_node import MergeResultNode
from fourthsession.core.housing_agent.nodes.plan_node import PlanNode
from fourthsession.core.housing_agent.nodes.validate_plan_node import ValidatePlanNode
from fourthsession.core.housing_agent.state.agent_state import HousingAgentState


class HousingAgentGraphBuilder:
    """주택 에이전트 그래프 빌더."""

    def build(self) -> StateGraph:
        """그래프를 구성해 반환한다.

        Returns:
            StateGraph: 구성된 LangGraph 그래프.
        """
        graph = StateGraph(HousingAgentState)

        graph.add_node("plan", PlanNode())
        graph.add_node("validate", ValidatePlanNode())
        graph.add_node("execute", ExecuteNode())
        graph.add_node("merge", MergeResultNode())
        graph.add_node("feedback", FeedbackLoopNode())
        graph.add_node("answer", AnswerNode())

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
        if bool(finalized):
            return "answer"
        return "plan"
