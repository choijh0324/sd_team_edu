# 목적: 번역 입력을 정규화하는 노드를 정의한다.
# 설명: 언어 코드와 텍스트를 기본 규칙으로 정리한다.
# 디자인 패턴: 파이프라인 노드
# 참조: firstsession/core/translate/graphs/translate_graph.py

"""입력 정규화 노드 모듈."""

from firstsession.core.translate.state.translation_state import TranslationState


class NormalizeInputNode:
    """입력 정규화를 담당하는 노드."""

    def run(self, state: TranslationState) -> TranslationState:
        """입력 데이터를 정규화한다.

        Args:
            state: 현재 번역 상태.

        Returns:
            TranslationState: 정규화된 상태.
        """
        normalized_state = dict(state)
        normalized_state["source_language"] = self._normalize_language_code(
            state.get("source_language", "")
        )
        normalized_state["target_language"] = self._normalize_language_code(
            state.get("target_language", "")
        )

        text = state.get("text", "")
        normalized_text = self._normalize_text(text)
        normalized_state["normalized_text"] = normalized_text

        if not normalized_text:
            normalized_state["error"] = "번역할 텍스트가 비어 있습니다."

        return normalized_state

    def _normalize_language_code(self, language_code: str) -> str:
        """언어 코드를 표준화한다."""
        cleaned = language_code.strip().replace("_", "-").lower()
        return cleaned

    def _normalize_text(self, text: str) -> str:
        """텍스트를 정리한다."""
        collapsed = " ".join(text.split())
        return collapsed.strip()
