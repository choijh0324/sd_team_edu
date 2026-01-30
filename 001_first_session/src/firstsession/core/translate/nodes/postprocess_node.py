# 목적: 번역 결과를 후처리하는 노드를 정의한다.
# 설명: 결과 검증과 정규화를 수행한다.
# 디자인 패턴: 파이프라인 노드
# 참조: firstsession/core/translate/graphs/translate_graph.py

"""후처리 노드 모듈."""

from firstsession.core.translate.state.translation_state import TranslationState


class PostprocessNode:
    """번역 결과 후처리를 담당하는 노드."""

    def run(self, state: TranslationState) -> TranslationState:
        """번역 결과를 검증하고 정리한다.

        Args:
            state: 현재 번역 상태.

        Returns:
            TranslationState: 후처리된 상태.
        """
        updated_state = dict(state)
        translated_text = updated_state.get("translated_text", "")
        normalized_text = " ".join(translated_text.split()).strip()
        updated_state["translated_text"] = normalized_text

        if not normalized_text:
            updated_state["error"] = "번역 결과가 비어 있습니다."
            updated_state["qc_passed"] = "NO"

        return updated_state
