# 목적: 요약 전이 정책을 제공한다.
# 설명: turn_count 기준으로 요약 경로를 결정한다.
# 디자인 패턴: Policy
# 참조: secondsession/core/chat/nodes/decide_summary_node.py

"""요약 전이 정책 모듈."""


class SummaryRoutePolicy:
    """요약 전이 정책."""

    def __init__(self, threshold: int = 5) -> None:
        """요약 분기 기준을 설정한다.

        Args:
            threshold: 요약 분기 기준 턴 수(초과 시 요약).
        """
        self._threshold = threshold

    def decide(self, turn_count: int) -> str:
        """turn_count에 따라 요약/종료 경로를 반환한다."""
        if turn_count > self._threshold:
            return "summarize"
        return "end"
