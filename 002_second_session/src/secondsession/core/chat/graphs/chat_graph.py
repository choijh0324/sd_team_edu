# 목적: 대화 그래프를 구성한다.
# 설명: 답변 생성 → 대화 누적 → 요약 여부 판단 흐름을 정의한다.
# 디자인 패턴: 파이프라인 + 빌더
# 참조: secondsession/core/chat/nodes/answer_node.py, secondsession/core/chat/nodes/append_history_node.py

"""대화 그래프 구성 모듈."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from secondsession.core.chat.const import ErrorCode, SafeguardLabel
from secondsession.core.chat.nodes.answer_node import AnswerNode
from secondsession.core.chat.nodes.append_history_node import AppendHistoryNode
from secondsession.core.chat.nodes.decide_summary_node import DecideSummaryNode
from secondsession.core.chat.nodes.fallback_node import FallbackNode
from secondsession.core.chat.nodes.safeguard_node import SafeguardNode
from secondsession.core.chat.nodes.summary_node import SummaryNode
from secondsession.core.chat.state.chat_state import ChatState
from secondsession.core.common.llm_client import LlmClient


class ChatGraph:
    """대화 그래프 실행기."""

    def __init__(
        self,
        checkpointer: Any | None = None,
        llm_client: LlmClient | None = None,
    ) -> None:
        """그래프를 초기화한다.

        Args:
            checkpointer: LangGraph 체크포인터 인스턴스.
            llm_client: LLM 클라이언트(선택).
        """
        self._checkpointer = checkpointer
        self._llm_client = llm_client
        self._app = self._build_graph()

    def run(self, state: ChatState) -> ChatState:
        """대화 그래프를 실행한다.

        Args:
            state: 대화 입력 상태.

        Returns:
            ChatState: 대화 결과 상태.
        """
        # thread_id를 config에 넣어 체크포인트 복구를 활성화한다.
        config = self._build_config(state)
        if config is None:
            return self._app.invoke(state)
        return self._app.invoke(state, config)

    def _build_config(self, state: ChatState) -> dict | None:
        """체크포인터 복구를 위한 실행 설정을 구성한다."""
        thread_id = state.get("thread_id")
        if not thread_id:
            return None
        configurable: dict[str, str] = {"thread_id": str(thread_id)}
        checkpoint_id = state.get("checkpoint_id")
        if checkpoint_id:
            configurable["checkpoint_id"] = str(checkpoint_id)
        return {"configurable": configurable}

    def _route_by_safeguard(self, state: ChatState) -> str:
        """안전 라벨에 따른 분기 정책을 정의한다.

        구현 내용:
            - SafeguardLabel 기준으로 PASS만 통과한다.
            - PASS가 아닌 경우 SAFEGUARD 에러 코드로 전환한다.
        """
        label = self._normalize_label(state.get("safeguard_label"))
        if label == SafeguardLabel.PASS:
            return "answer"
        state["error_code"] = ErrorCode.SAFEGUARD
        return "fallback"

    def _normalize_label(self, value: SafeguardLabel | str | None) -> SafeguardLabel | None:
        """안전 라벨 값을 정규화한다."""
        if value is None:
            return None
        if isinstance(value, SafeguardLabel):
            return value
        try:
            return SafeguardLabel[str(value).upper()]
        except KeyError:
            return None

    def _build_graph(self) -> object:
        """대화 그래프를 구성한다.

        Returns:
            object: 컴파일된 LangGraph 애플리케이션.
        """
        graph = StateGraph(ChatState)
        safeguard_node = SafeguardNode(self._llm_client)
        answer_node = AnswerNode(self._llm_client)
        fallback_node = FallbackNode()
        append_history_node = AppendHistoryNode()
        decide_summary_node = DecideSummaryNode()
        summary_node = SummaryNode(self._llm_client)

        graph.add_node("safeguard", safeguard_node.run)
        graph.add_node("answer", answer_node.run)
        graph.add_node("fallback", fallback_node.run)
        graph.add_node("append_history", append_history_node.run)
        graph.add_node("decide_summary", decide_summary_node.run)
        graph.add_node("summarize", summary_node.run)

        graph.set_entry_point("safeguard")
        graph.add_conditional_edges("safeguard", self._route_by_safeguard, {
            "answer": "answer",
            "fallback": "fallback",
        })
        graph.add_conditional_edges("answer", self._route_after_answer, {
            "append_history": "append_history",
            "fallback": "fallback",
        })
        graph.add_edge("append_history", "decide_summary")

        graph.add_conditional_edges("decide_summary", lambda s: s["route"], {
            "summarize": "summarize",
            "end": END,
        })
        graph.add_edge("fallback", "append_history")
        graph.add_edge("summarize", END)

        # 폴백 응답도 history에 기록한다.

        if self._checkpointer is None:
            return graph.compile()
        return graph.compile(checkpointer=self._checkpointer)

    def _route_after_answer(self, state: ChatState) -> str:
        """answer 결과에 따라 fallback 여부를 결정한다."""
        error_code = state.get("error_code")
        if error_code is None:
            return "append_history"
        return "fallback"
