# 목적: 대화 내역을 상태에 누적한다.
# 설명: turn_count를 증가시키고 history를 업데이트한다.
# 디자인 패턴: 커맨드
# 참조: secondsession/core/chat/graphs/chat_graph.py

"""대화 내역 업데이트 노드 모듈."""

import os

try:
    import redis
except ImportError:  # pragma: no cover - 환경 구성에 따라 달라짐
    redis = None

from secondsession.core.chat.const.message_normalizer import (
    build_message_id,
    normalize_assistant_message,
    normalize_system_message,
    normalize_user_message,
)
from secondsession.core.chat.repository import ChatHistoryRepository
from secondsession.core.chat.state.chat_state import ChatState


def append_history_node(state: ChatState) -> dict:
    """대화 내역을 갱신한다.

    TODO:
        - history에 사용자/어시스턴트 메시지를 추가한다.
        - turn_count를 1 증가시킨다.
        - reducer가 누적하므로 history는 신규 항목만 반환한다.
        - reducer가 누적하므로 turn_count는 증가분만 반환한다.
        - ChatHistoryItem(Pydantic)으로 항목을 검증한다.
    """
    history = state.get("history", [])
    summary = state.get("summary")
    user_message = state.get("last_user_message", "")
    assistant_message = state.get("last_assistant_message") or ""
    trace_id = state.get("trace_id") or "unknown"
    seq = int(state.get("seq") or 0)
    user_message_id = build_message_id(trace_id, seq + 1)
    assistant_message_id = build_message_id(trace_id, seq + 2)
    new_items: list[dict] = []
    if summary and _should_append_summary(history, summary):
        summary_message_id = build_message_id(trace_id, seq)
        summary_item = normalize_system_message(
            f"요약: {summary}",
            message_id=summary_message_id,
        ).model_dump()
        new_items.append(summary_item)

    user_item = normalize_user_message(
        user_message,
        message_id=user_message_id,
    ).model_dump()
    assistant_item = normalize_assistant_message(
        assistant_message,
        message_id=assistant_message_id,
    ).model_dump()

    new_items.extend([user_item, assistant_item])
    _persist_history(state, new_items)
    return {
        "history": new_items,
        "turn_count": 1,
        "seq": seq + len(new_items),
    }


def _should_append_summary(history: list[dict], summary: str) -> bool:
    """요약 메시지를 history에 추가할지 판단한다."""
    if not history:
        return True
    last = history[-1]
    if last.get("role") != "system":
        return True
    content = last.get("content", "")
    return content != f"요약: {summary}"


def _persist_history(state: ChatState, new_items: list[dict]) -> None:
    """외부 저장소에 대화 내역을 저장한다."""
    user_id = state.get("user_id")
    thread_id = state.get("thread_id")
    if not user_id or not thread_id or redis is None:
        return
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    client = redis.Redis.from_url(redis_url)
    repo = ChatHistoryRepository(client)
    for item in new_items:
        repo.append_item(user_id, thread_id, item)
