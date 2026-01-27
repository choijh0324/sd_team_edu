# 목적: 사용자 입력에 대한 답변을 생성한다.
# 설명: LLM 호출을 통해 응답을 만든다.
# 디자인 패턴: 커맨드
# 참조: secondsession/core/chat/graphs/chat_graph.py

"""대화 응답 생성 노드 모듈."""

from secondsession.core.chat.prompts.answer_prompt import ANSWER_PROMPT
from secondsession.core.chat.state.chat_state import ChatState


def answer_node(state: ChatState) -> dict:
    """사용자 입력에 대한 답변을 생성한다.

    TODO:
        - LLM 클라이언트를 연결한다.
        - ANSWER_PROMPT.format으로 사용자 입력을 결합한다.
        - state["last_user_message"]를 기반으로 답변을 생성한다.
        - 결과를 last_assistant_message로 반환한다.
        - 응답 스키마(Pydantic) 검증 실패 시 error_code를 설정한다.
        - 도구 호출 실패/타임아웃 시 error_code를 설정한다.
        - error_code가 설정된 경우 폴백 라우팅 흐름을 고려한다.
        - ErrorCode(Enum)로 에러 유형을 고정한다.
    """
    _ = state["last_user_message"]
    _ = ANSWER_PROMPT
    raise NotImplementedError("답변 생성 로직을 구현해야 합니다.")
