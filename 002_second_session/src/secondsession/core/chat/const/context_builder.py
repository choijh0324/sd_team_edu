# 목적: 요약과 최근 메시지를 조합해 컨텍스트를 구성한다.
# 설명: summary를 시스템 메시지로 앞에 배치한다.
# 디자인 패턴: 파이프라인
# 참조: docs/04_memory/03_컨텍스트_윈도우_및_트리밍.md

"""컨텍스트 빌더 모듈."""

from secondsession.core.chat.const.message_normalizer import normalize_system_message


def build_context(summary: str | None, recent_messages: list[dict]) -> list[dict]:
    """요약과 최근 메시지를 합쳐 컨텍스트를 만든다."""
    if not summary:
        return recent_messages
    summary_item = normalize_system_message(f"요약: {summary}").model_dump()
    return [summary_item] + recent_messages
