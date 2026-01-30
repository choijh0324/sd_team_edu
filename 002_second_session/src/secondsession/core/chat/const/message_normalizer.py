# 목적: 외부 입력을 내부 메시지 포맷으로 정규화한다.
# 설명: role/content/created_at/metadata를 표준화한다.
# 디자인 패턴: Adapter
# 참조: docs/04_memory/02_메시지_타입과_정규화.md

"""메시지 정규화 유틸리티 모듈."""

from datetime import datetime, timezone

from secondsession.core.chat.const.chat_history_item import ChatHistoryItem


def normalize_user_message(
    content: str,
    metadata: dict | None = None,
    message_id: str | None = None,
) -> ChatHistoryItem:
    """사용자 메시지를 내부 포맷으로 정규화한다."""
    return ChatHistoryItem(
        role="user",
        content=content,
        created_at=_utc_now(),
        metadata=metadata or {},
        message_id=message_id,
    )


def normalize_assistant_message(
    content: str,
    metadata: dict | None = None,
    message_id: str | None = None,
) -> ChatHistoryItem:
    """어시스턴트 메시지를 내부 포맷으로 정규화한다."""
    return ChatHistoryItem(
        role="assistant",
        content=content,
        created_at=_utc_now(),
        metadata=metadata or {},
        message_id=message_id,
    )


def normalize_system_message(
    content: str,
    metadata: dict | None = None,
    message_id: str | None = None,
) -> ChatHistoryItem:
    """시스템 메시지를 내부 포맷으로 정규화한다."""
    return ChatHistoryItem(
        role="system",
        content=content,
        created_at=_utc_now(),
        metadata=metadata or {},
        message_id=message_id,
    )


def normalize_tool_message(
    content: str,
    tool_name: str,
    tool_args: dict | None = None,
    tool_result: dict | None = None,
    message_id: str | None = None,
) -> ChatHistoryItem:
    """툴 메시지를 내부 포맷으로 정규화한다."""
    return ChatHistoryItem(
        role="tool",
        content=content,
        created_at=_utc_now(),
        metadata={
            "tool_name": tool_name,
            "tool_args": tool_args or {},
            "tool_result": tool_result or {},
        },
        message_id=message_id,
    )


def _utc_now() -> str:
    """UTC ISO8601 시각을 반환한다."""
    return datetime.now(timezone.utc).isoformat()


def build_message_id(trace_id: str, seq: int) -> str:
    """스트리밍 메시지 식별자를 만든다."""
    return f"{trace_id}:{seq}"
