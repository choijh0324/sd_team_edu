# 목적: 재번역을 수행하는 노드를 정의한다.
# 설명: QC 실패 시 재시도 프롬프트로 번역을 복구한다.
# 디자인 패턴: 전략 패턴 + 파이프라인 노드
# 참조: docs/04_string_tricks/05_retry_logic.md

"""재번역 노드 모듈."""

from firstsession.core.translate.nodes.call_model_node import CallModelNode
from firstsession.core.translate.prompts.retry_translate_prompt import (
    RETRY_TRANSLATE_PROMPT,
)
from firstsession.core.translate.state.translation_state import TranslationState


class RetryTranslateNode:
    """재번역을 담당하는 노드."""

    def run(self, state: TranslationState) -> TranslationState:
        """재번역을 수행한다.

        Args:
            state: 현재 번역 상태.

        Returns:
            TranslationState: 재번역 결과가 포함된 상태.
        """
        source_text = state.get("normalized_text") or state.get("text", "")
        failed_translation = state.get("translated_text", "")
        prompt = RETRY_TRANSLATE_PROMPT.format(
            source_text=source_text,
            failed_translation=failed_translation,
        )
        improved_translation = CallModelNode().run(prompt)

        updated_state = dict(state)
        updated_state["translated_text"] = improved_translation
        return updated_state
