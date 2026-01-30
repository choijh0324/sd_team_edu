# 목적: 에러 코드 기반 전이 정책을 제공한다.
# 설명: error_code 존재 여부로 폴백 경로를 결정한다.
# 디자인 패턴: Policy
# 참조: secondsession/core/chat/nodes/decide_summary_node.py

"""에러 기반 전이 정책 모듈."""

from secondsession.core.chat.const.error_code import ErrorCode


class ErrorRoutePolicy:
    """에러 코드 기반 전이 정책."""

    def decide(self, error_code: ErrorCode | None) -> dict | None:
        """에러 코드 존재 시 폴백 전이 정보를 반환한다."""
        if error_code:
            return {
                "route": "fallback",
                "user_message": error_code.user_message,
            }
        return None
