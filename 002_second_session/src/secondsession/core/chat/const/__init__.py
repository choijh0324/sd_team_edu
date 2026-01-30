# 목적: 대화 코어 상수/스키마를 외부에 노출한다.
# 설명: 에러 코드/라벨/스키마를 집계한다.
# 디자인 패턴: 파사드
# 참조: secondsession/core/chat/const/error_code.py

"""대화 코어 상수 패키지."""

from secondsession.core.chat.const.error_code import ErrorCode
from secondsession.core.chat.const.safeguard_label import SafeguardLabel
from secondsession.core.chat.const.chat_history_item import ChatHistoryItem
from secondsession.core.chat.const.message_normalizer import (
    normalize_assistant_message,
    normalize_system_message,
    normalize_tool_message,
    normalize_user_message,
)
from secondsession.core.chat.const.trim_policy import (
    DEFAULT_CONTEXT_BUDGET,
    DEFAULT_CONTEXT_BUDGET_ENV,
    DEFAULT_CONTEXT_BUDGET_MODEL_ENV,
    get_context_budget,
    get_context_budget_by_model,
    trim_recent,
    trim_keep_system,
    trim_keep_system_and_tool,
    trim_by_budget,
)
from secondsession.core.chat.const.context_builder import build_context

__all__ = [
    "ErrorCode",
    "SafeguardLabel",
    "ChatHistoryItem",
    "normalize_user_message",
    "normalize_assistant_message",
    "normalize_system_message",
    "normalize_tool_message",
    "DEFAULT_CONTEXT_BUDGET",
    "DEFAULT_CONTEXT_BUDGET_ENV",
    "DEFAULT_CONTEXT_BUDGET_MODEL_ENV",
    "get_context_budget",
    "get_context_budget_by_model",
    "trim_recent",
    "trim_keep_system",
    "trim_keep_system_and_tool",
    "trim_by_budget",
    "build_context",
]
