# 목적: 대화 그래프를 구성한다.
# 설명: 답변 생성 → 대화 누적 → 요약 여부 판단 흐름을 정의한다.
# 디자인 패턴: 파이프라인
# 참조: secondsession/core/chat/nodes/answer_node.py, secondsession/core/chat/nodes/append_history_node.py

"""대화 그래프 구성 모듈."""

from datetime import datetime, timezone
from langgraph.graph import StateGraph, END

from secondsession.core.chat.const.error_code import ErrorCode
from secondsession.core.chat.const.safeguard_label import SafeguardLabel
from secondsession.core.chat.state.chat_state import ChatState
from secondsession.core.chat.nodes.answer_node import answer_node
from secondsession.core.chat.nodes.append_history_node import append_history_node
from secondsession.core.chat.nodes.decide_summary_node import decide_summary_node
from secondsession.core.chat.nodes.summary_node import summary_node
from secondsession.core.chat.nodes.safeguard_node import safeguard_node
from secondsession.core.chat.nodes.fallback_node import fallback_node


def route_by_safeguard(state: ChatState) -> str:
    """안전 라벨에 따른 분기 정책을 정의한다.

    전이표(요약):
        - safeguard_label == PASS -> answer
        - safeguard_label != PASS -> fallback (error_code=SAFEGUARD)

    TODO:
        - safeguard_label 기준 분기 정책을 구현한다.
        - PASS가 아닌 경우 error_code를 설정하도록 연결한다.
        - 정책/규제 요구사항을 반영한다.
        - 라벨별로 폴백 메시지/차단 로직을 분리한다.
        - SafeguardLabel(Enum)을 사용해 분기 값을 고정한다.
    """
    label = state.get("safeguard_label")
    if label == SafeguardLabel.PASS:
        return "answer"
    if label is not None:
        state["error_code"] = ErrorCode.SAFEGUARD
        state["user_message"] = ErrorCode.SAFEGUARD.user_message
    return "fallback"


def build_chat_graph(checkpointer) -> object:
    """대화 그래프를 생성한다.

    Args:
        checkpointer: LangGraph 체크포인터 인스턴스.

    Returns:
        object: 컴파일된 LangGraph 애플리케이션.
    """
    graph = StateGraph(ChatState)
    graph.add_node("safeguard", _wrap_node("safeguard", safeguard_node, checkpointer))
    graph.add_node("answer", _wrap_node("answer", answer_node, checkpointer))
    graph.add_node("fallback", _wrap_node("fallback", fallback_node, checkpointer))
    graph.add_node("append_history", _wrap_node("append_history", append_history_node, checkpointer))
    graph.add_node("decide_summary", _wrap_node("decide_summary", decide_summary_node, checkpointer))
    graph.add_node("summarize", _wrap_node("summarize", summary_node, checkpointer))

    graph.set_entry_point("safeguard")
    graph.add_conditional_edges("safeguard", route_by_safeguard, {
        "answer": "answer",
        "fallback": "fallback",
    })
    graph.add_conditional_edges("answer", lambda s: "fallback" if s.get("error_code") else "append_history", {
        "fallback": "fallback",
        "append_history": "append_history",
    })
    graph.add_edge("append_history", "decide_summary")

    graph.add_conditional_edges("decide_summary", lambda s: s["route"], {
        "summarize": "summarize",
        "end": END,
    })
    graph.add_edge("fallback", END)
    graph.add_edge("summarize", END)

    # TODO:
    # - thread_id를 config에 넣어 체크포인트 복구를 활성화하세요.
    # - 복구된 history를 기반으로 답변을 이어가도록 구성하세요.
    # - 폴백 응답도 필요한 경우 history에 기록하도록 정책을 정하세요.
    # - answer 단계의 에러(error_code)를 fallback으로 라우팅하는 경로를 추가하세요.

    return graph.compile(checkpointer=checkpointer)


def _wrap_node(node_name: str, handler, checkpointer):
    """노드 실행 후 체크포인트를 저장하는 래퍼."""

    def _wrapped(state: ChatState) -> dict:
        updated = handler(state)
        snapshot = dict(state)
        if isinstance(updated, dict):
            snapshot.update(updated)
        thread_id = snapshot.get("thread_id")
        if thread_id and hasattr(checkpointer, "save"):
            checkpointer.save(
                thread_id=thread_id,
                state=snapshot,
                metadata={
                    "node": node_name,
                    "route": snapshot.get("route"),
                    "error_code": snapshot.get("error_code"),
                    "safeguard_label": snapshot.get("safeguard_label"),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        return updated

    return _wrapped
