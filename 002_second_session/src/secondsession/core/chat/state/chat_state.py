# 목적: 대화 그래프의 상태 스키마를 정의한다.
# 설명: 대화 내역과 요약 정보를 포함한 상태를 관리한다.
# 디자인 패턴: 상태 객체
# 참조: secondsession/core/chat/graphs/chat_graph.py

"""대화 그래프 상태 스키마 모듈."""

from typing import Annotated, TypedDict

from secondsession.core.chat.const import ErrorCode, SafeguardLabel
from secondsession.core.chat.const.chat_history_item import ChatHistoryItem

def trim_recent_history(items: list[dict], limit: int = 20) -> list[dict]:
    """최근 N턴 기준으로 history를 제한한다."""
    if limit <= 0:
        return []
    return items[-limit:]

def add_history(existing: list[dict], incoming: list[dict] | None) -> list[dict]:
    """대화 내역을 누적한다.

    구현 내용:
        - history 항목은 ChatHistoryItem 스키마를 따른다.
        - 최근 N턴만 유지한다.
    """
    if incoming is None:
        return existing
    merged = existing + incoming
    return trim_recent_history(merged, limit=20)


def add_turn(existing: int, incoming: int | None) -> int:
    """턴 수를 누적한다."""
    if incoming is None:
        return existing
    return existing + incoming


def add_candidates(existing: list[str], incoming: list[str] | None) -> list[str]:
    """병렬 후보 응답을 누적한다."""
    if incoming is None:
        return existing
    return existing + incoming


def add_candidate_scores(existing: list[float], incoming: list[float] | None) -> list[float]:
    """병렬 후보 점수를 누적한다."""
    if incoming is None:
        return existing
    return existing + incoming


def add_candidate_errors(existing: list[str], incoming: list[str] | None) -> list[str]:
    """병렬 후보 에러를 누적한다."""
    if incoming is None:
        return existing
    return existing + incoming


class ChatState(TypedDict):
    """대화 그래프 상태 스키마."""

    history: Annotated[list[ChatHistoryItem], add_history]
    summary: str | None
    turn_count: Annotated[int, add_turn]
    last_user_message: str
    last_assistant_message: str | None
    candidates: Annotated[list[str], add_candidates]
    candidate_scores: Annotated[list[float], add_candidate_scores]
    candidate_errors: Annotated[list[str], add_candidate_errors]
    selected_candidate: str | None
    # 폴백 메시지 정책:
    # - safeguard_label이 PASS가 아니면 SAFEGUARD 에러를 우선한다.
    # - error_code가 있으면 ErrorCode.user_message를 사용한다.
    safeguard_label: SafeguardLabel | None
    route: str | None
    error_code: ErrorCode | None
    trace_id: str | None
    thread_id: str | None
    session_id: str | None
    history_persisted: bool | None
    checkpoint_ref: str | None
