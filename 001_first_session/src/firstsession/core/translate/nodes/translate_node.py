# 목적: 번역을 수행하는 노드를 정의한다.
# 설명: 프롬프트 생성과 모델 호출을 포함할 수 있다.
# 디자인 패턴: 전략 패턴 + 파이프라인 노드
# 참조: docs/04_string_tricks/05_retry_logic.md

"""번역 수행 노드 모듈."""

from firstsession.core.translate.nodes.call_model_node import CallModelNode
from firstsession.core.translate.prompts.translation_prompt import TRANSLATION_PROMPT
from firstsession.core.translate.state.translation_state import TranslationState


class TranslateNode:
    """번역 수행을 담당하는 노드."""

    def run(self, state: TranslationState) -> TranslationState:
        """번역 결과를 생성한다.

        Args:
            state: 현재 번역 상태.

        Returns:
            TranslationState: 번역 결과가 포함된 상태.
        """
        source_language = state.get("source_language", "")
        target_language = state.get("target_language", "")
        text = state.get("normalized_text") or state.get("text", "")

        prompt = TRANSLATION_PROMPT.format(
            source_language=source_language,
            target_language=target_language,
            text=text,
        )
        translated_text = CallModelNode().run(prompt)

        updated_state = dict(state)
        updated_state["translated_text"] = translated_text
        return updated_state
