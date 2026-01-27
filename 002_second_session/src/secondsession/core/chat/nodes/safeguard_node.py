# 목적: 안전 분류 노드를 정의한다.
# 설명: 사용자 입력을 안전 라벨로 분류한다.
# 디자인 패턴: 커맨드
# 참조: secondsession/core/chat/graphs/chat_graph.py

"""안전 분류 노드 모듈."""

from secondsession.core.chat.prompts.safeguard_prompt import SAFEGUARD_PROMPT
from secondsession.core.chat.state.chat_state import ChatState


def safeguard_node(state: ChatState) -> dict:
    """사용자 입력을 안전 라벨로 분류한다.

    TODO:
        - LLM 클라이언트를 연결한다.
        - SAFEGUARD_PROMPT.format으로 사용자 입력을 결합한다.
        - 결과 라벨을 safeguard_label로 반환한다.
        - PASS가 아닌 경우 error_code를 설정하는 정책을 정의한다.
        - 라벨별 사용자 메시지/차단 정책을 문서화한다.
        - SafeguardLabel/ErrorCode(Enum)을 사용해 값을 고정한다.
    """
    _ = SAFEGUARD_PROMPT
    _ = state.get("last_user_message", "")
    raise NotImplementedError("안전 분류 로직을 구현해야 합니다.")
