# 목적: 안전 분류 결과를 바탕으로 진행/차단 결정을 기록한다.
# 설명: PASS 여부를 판단하고 차단 시 오류 메시지를 설정한다.
# 디자인 패턴: 파이프라인 노드
# 참조: firstsession/core/translate/const/safeguard_messages.py

"""안전 분류 결정 노드 모듈."""

from firstsession.core.translate.const.safeguard_messages import SafeguardMessage
from firstsession.core.translate.state.translation_state import TranslationState


class SafeguardDecisionNode:
    """안전 분류 결정을 담당하는 노드."""

    def run(self, state: TranslationState) -> TranslationState:
        """PASS 여부와 오류 메시지를 기록한다.

        Args:
            state: 현재 번역 상태.

        Returns:
            TranslationState: 결정 결과가 포함된 상태.
        """
        updated_state = dict(state)
        label = state.get("safeguard_label", "")
        if label == "PASS":
            updated_state["error"] = ""
            return updated_state

        message_map = {
            "PII": SafeguardMessage.PII.value,
            "HARMFUL": SafeguardMessage.HARMFUL.value,
            "PROMPT_INJECTION": SafeguardMessage.PROMPT_INJECTION.value,
        }
        updated_state["error"] = message_map.get(
            label, "안전 분류 결과를 확인할 수 없습니다."
        )
        return updated_state
