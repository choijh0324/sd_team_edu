# 목적: 대화 요약 노드를 정의한다.
# 설명: 대화 내역을 요약해 summary에 저장한다.
# 디자인 패턴: 커맨드
# 참조: secondsession/core/chat/graphs/chat_graph.py

"""대화 요약 노드 모듈."""

from secondsession.core.chat.state.chat_state import ChatState
from secondsession.core.chat.prompts.summary_prompt import SUMMARY_PROMPT


def summary_node(state: ChatState) -> dict:
    """대화 요약을 생성한다.

    TODO:
        - LLM 클라이언트를 연결한다.
        - SUMMARY_PROMPT.format으로 state["history"]를 결합한다.
        - summary 값을 반환한다.
    """
    _ = SUMMARY_PROMPT
    _ = state.get("history", [])
    raise NotImplementedError("요약 노드 로직을 구현해야 합니다.")
