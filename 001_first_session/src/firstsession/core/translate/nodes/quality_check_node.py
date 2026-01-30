# 목적: 번역 품질을 검사하는 노드를 정의한다.
# 설명: 원문과 번역문을 비교해 YES/NO로 통과 여부를 판단한다.
# 디자인 패턴: 전략 패턴 + 파이프라인 노드
# 참조: docs/04_string_tricks/01_yes_no_파서.md

"""번역 품질 검사 노드 모듈."""

from firstsession.core.translate.nodes.call_model_node import CallModelNode
from firstsession.core.translate.prompts.quality_check_prompt import (
    QUALITY_CHECK_PROMPT,
)
from firstsession.core.translate.state.translation_state import TranslationState


class QualityCheckNode:
    """번역 품질 검사를 담당하는 노드."""

    def run(self, state: TranslationState) -> TranslationState:
        """번역 품질을 검사한다.

        Args:
            state: 현재 번역 상태.

        Returns:
            TranslationState: 품질 검사 결과가 포함된 상태.
        """
        source_text = state.get("normalized_text") or state.get("text", "")
        translated_text = state.get("translated_text", "")

        prompt = QUALITY_CHECK_PROMPT.format(
            source_text=source_text,
            translated_text=translated_text,
        )
        raw_output = CallModelNode().run(prompt)
        qc_passed = self._normalize_decision(raw_output)

        updated_state = dict(state)
        updated_state["qc_passed"] = qc_passed
        return updated_state

    def _normalize_decision(self, raw_output: str) -> str:
        """모델 출력에서 YES/NO를 정규화한다."""
        cleaned = raw_output.strip().upper()
        if cleaned == "YES":
            return "YES"
        if cleaned == "NO":
            return "NO"
        return "NO"
