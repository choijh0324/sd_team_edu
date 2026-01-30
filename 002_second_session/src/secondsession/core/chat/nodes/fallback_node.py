# 목적: 폴백 응답 노드를 정의한다.
# 설명: 안전/에러 상황에서 사용자에게 최소 안내를 제공한다.
# 디자인 패턴: 커맨드
# 참조: secondsession/core/chat/graphs/chat_graph.py

"""폴백 응답 노드 모듈."""

import logging

from secondsession.core.chat.const.error_code import ErrorCode
from secondsession.core.chat.const.safeguard_label import SafeguardLabel
from secondsession.core.chat.state.chat_state import ChatState


def fallback_node(state: ChatState) -> dict:
    """폴백 응답을 생성한다.

    TODO:
        - error_code와 safeguard_label을 기반으로 폴백 메시지를 결정한다.
        - last_assistant_message에 폴백 응답을 담아 반환한다.
        - 필요한 경우 로그/메트릭을 추가한다.
        - 사용자 메시지 정책(톤/완화)을 enum 테이블로 관리한다.
        - ErrorCode/SafeguardLabel(Enum)을 기준으로 정책을 분기한다.
    """
    logger = logging.getLogger(__name__)
    error_code = state.get("error_code")
    safeguard_label = state.get("safeguard_label")

    resolved_error_code = error_code
    if safeguard_label and safeguard_label != SafeguardLabel.PASS:
        resolved_error_code = ErrorCode.SAFEGUARD

    message = _resolve_fallback_message(
        error_code=resolved_error_code,
        safeguard_label=safeguard_label,
    )
    logger.warning(
        "폴백 응답 생성: error_code=%s, safeguard_label=%s",
        resolved_error_code.code if resolved_error_code else None,
        safeguard_label.value if safeguard_label else None,
    )

    return {
        "last_assistant_message": message,
        "error_code": resolved_error_code or ErrorCode.UNKNOWN,
    }


def _resolve_fallback_message(
    error_code: ErrorCode | None,
    safeguard_label: SafeguardLabel | None,
) -> str:
    """폴백 메시지를 결정한다."""
    if safeguard_label and safeguard_label != SafeguardLabel.PASS:
        return ErrorCode.SAFEGUARD.user_message
    if error_code:
        return error_code.user_message
    return ErrorCode.UNKNOWN.user_message
