# 목적: 재번역 가능 여부를 판단한다.
# 설명: retry_count와 qc_passed를 기준으로 다음 경로를 결정한다.
# 디자인 패턴: 파이프라인 노드
# 참조: docs/04_string_tricks/05_retry_logic.md

"""재번역 게이트 노드 모듈."""

from firstsession.core.translate.state.translation_state import TranslationState


class RetryGateNode:
    """재번역 가능 여부를 판단하는 노드."""

    def run(self, state: TranslationState) -> TranslationState:
        """재번역 가능 여부를 판단한다.

        Args:
            state: 현재 번역 상태.

        Returns:
            TranslationState: 게이트 판단 결과가 포함된 상태.
        """
        updated_state = dict(state)
        qc_passed = updated_state.get("qc_passed", "")
        if qc_passed == "YES":
            return updated_state

        updated_state["retry_count"] = int(
            updated_state.get("retry_count", 0) or 0
        ) + 1

        retry_count = int(updated_state.get("retry_count", 0) or 0)
        max_retry_count = int(updated_state.get("max_retry_count", 3) or 3)
        updated_state["max_retry_count"] = max_retry_count

        if retry_count < max_retry_count:
            return updated_state

        updated_state["error"] = "재시도 횟수 초과로 번역을 완료하지 못했습니다."
        return updated_state
