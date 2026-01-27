# 목적: 대화 코어 모듈을 외부에 노출한다.
# 설명: 그래프/노드/프롬프트 패키지를 집계한다.
# 디자인 패턴: 파사드
# 참조: secondsession/core/chat/graphs, secondsession/core/chat/nodes

"""대화 코어 패키지."""

from secondsession.core.chat.graphs import build_chat_graph, ChatState
from secondsession.core.chat.nodes import (
    summary_node,
    answer_node,
    safeguard_node,
    fallback_node,
    append_history_node,
    decide_summary_node,
)
from secondsession.core.chat.prompts import ANSWER_PROMPT, SAFEGUARD_PROMPT, SUMMARY_PROMPT

__all__ = [
    "build_chat_graph",
    "ChatState",
    "summary_node",
    "answer_node",
    "safeguard_node",
    "fallback_node",
    "append_history_node",
    "decide_summary_node",
    "ANSWER_PROMPT",
    "SAFEGUARD_PROMPT",
    "SUMMARY_PROMPT",
]
