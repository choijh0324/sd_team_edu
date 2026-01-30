# 목적: 최종 응답을 구성하는 노드를 정의한다.
# 설명: 상태를 API 응답으로 변환하기 전 정리한다.
# 디자인 패턴: 파이프라인 노드
# 참조: firstsession/api/translate/model/translation_response.py

"""응답 구성 노드 모듈."""

from firstsession.core.translate.state.translation_state import TranslationState


class ResponseNode:
    """응답 구성을 담당하는 노드."""

    def run(self, state: TranslationState) -> TranslationState:
        """최종 응답을 위한 상태를 정리한다.

        Args:
            state: 현재 번역 상태.

        Returns:
            TranslationState: 응답 구성이 완료된 상태.
        """
        error_message = state.get("error", "")
        translated_text = state.get("translated_text", "")

        response_state = {
            "source_language": state.get("source_language", ""),
            "target_language": state.get("target_language", ""),
            "translated_text": translated_text if not error_message else "",
            "error": error_message,
        }
        return response_state
