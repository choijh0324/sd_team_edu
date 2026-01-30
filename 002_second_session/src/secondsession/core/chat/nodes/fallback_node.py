# 목적: 폴백 응답 노드를 정의한다.
# 설명: 안전/에러 상황에서 사용자에게 최소 안내를 제공한다.
# 디자인 패턴: 전략 패턴 + 파이프라인 노드
# 참조: secondsession/core/chat/graphs/chat_graph.py

"""폴백 응답 노드 모듈."""

from secondsession.core.chat.const import ErrorCode, SafeguardLabel
from secondsession.core.chat.state.chat_state import ChatState


class FallbackNode:
    """폴백 응답을 생성하는 노드."""

    def run(self, state: ChatState) -> ChatState:
        """폴백 응답을 생성한다.

        Args:
            state: 현재 대화 상태.

        Returns:
            ChatState: 폴백 응답이 반영된 상태.
        """
        error_code = self._normalize_error_code(state.get("error_code"))
        safeguard_label = self._normalize_label(state.get("safeguard_label"))

        if error_code is None and safeguard_label not in (None, SafeguardLabel.PASS):
            error_code = ErrorCode.SAFEGUARD

        message = self._build_message(error_code, safeguard_label)
        response: ChatState = {
            "last_assistant_message": message,
        }
        if error_code is not None:
            response["error_code"] = error_code
        return response

    def _normalize_error_code(self, value: ErrorCode | str | None) -> ErrorCode | None:
        """에러 코드를 정규화한다."""
        if value is None:
            return None
        if isinstance(value, ErrorCode):
            return value
        for code in ErrorCode:
            if code.code == value:
                return code
        return None

    def _normalize_label(self, value: SafeguardLabel | str | None) -> SafeguardLabel | None:
        """안전 라벨을 정규화한다."""
        if value is None:
            return None
        if isinstance(value, SafeguardLabel):
            return value
        try:
            return SafeguardLabel[str(value).upper()]
        except KeyError:
            return None

    def _build_message(
        self,
        error_code: ErrorCode | None,
        safeguard_label: SafeguardLabel | None,
    ) -> str:
        """폴백 메시지를 생성한다."""
        if error_code is not None:
            return error_code.user_message
        if safeguard_label not in (None, SafeguardLabel.PASS):
            return ErrorCode.SAFEGUARD.user_message
        return ErrorCode.UNKNOWN.user_message
