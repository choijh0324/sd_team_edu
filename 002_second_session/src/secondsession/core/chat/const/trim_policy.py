# 목적: 대화 내역 트리밍 정책을 제공한다.
# 설명: 최근 메시지/시스템 메시지 보존 규칙을 분리한다.
# 디자인 패턴: 전략
# 참조: docs/04_memory/03_컨텍스트_윈도우_및_트리밍.md

"""트리밍 정책 모듈."""

import os

DEFAULT_CONTEXT_BUDGET = 1200
DEFAULT_CONTEXT_BUDGET_ENV = "CHAT_CONTEXT_BUDGET"
DEFAULT_CONTEXT_BUDGET_MODEL_ENV = "CHAT_CONTEXT_BUDGET_BY_MODEL"


def trim_recent(messages: list[dict], keep_last: int) -> list[dict]:
    """최근 N개 메시지만 유지한다."""
    if keep_last <= 0:
        return []
    return messages[-keep_last:]


def trim_keep_system(messages: list[dict], keep_last: int) -> list[dict]:
    """시스템 메시지를 유지하면서 최근 메시지를 보존한다."""
    system_msgs = [m for m in messages if m.get("role") == "system"]
    rest = [m for m in messages if m.get("role") != "system"]
    if keep_last <= 0:
        return system_msgs
    return system_msgs + rest[-keep_last:]


def trim_keep_system_and_tool(messages: list[dict], keep_last: int) -> list[dict]:
    """시스템/툴 메시지를 유지하면서 최근 메시지를 보존한다."""
    fixed_msgs = [m for m in messages if m.get("role") in {"system", "tool"}]
    rest = [m for m in messages if m.get("role") not in {"system", "tool"}]
    if keep_last <= 0:
        return fixed_msgs
    return fixed_msgs + rest[-keep_last:]


def trim_by_budget(messages: list[dict], budget: int) -> list[dict]:
    """간단한 길이 기반 근사치로 메시지를 제한한다."""
    if budget <= 0:
        return []
    selected: list[dict] = []
    total = 0
    for msg in reversed(messages):
        cost = len(msg.get("content", ""))
        if total + cost > budget:
            break
        selected.append(msg)
        total += cost
    return list(reversed(selected))


def get_context_budget() -> int:
    """환경변수를 우선해 컨텍스트 예산을 반환한다."""
    raw = os.getenv(DEFAULT_CONTEXT_BUDGET_ENV)
    if raw is None:
        return DEFAULT_CONTEXT_BUDGET
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_CONTEXT_BUDGET
    return value if value > 0 else DEFAULT_CONTEXT_BUDGET


def get_context_budget_by_model(model: str | None) -> int:
    """모델별 예산 설정을 확인한 뒤 기본값으로 폴백한다."""
    if not model:
        return get_context_budget()
    raw_map = os.getenv(DEFAULT_CONTEXT_BUDGET_MODEL_ENV, "")
    if not raw_map:
        return get_context_budget()
    pairs = [p for p in raw_map.split(",") if ":" in p]
    mapping = {}
    for pair in pairs:
        name, value = pair.split(":", 1)
        mapping[name.strip()] = value.strip()
    raw = mapping.get(model)
    if raw is None:
        return get_context_budget()
    try:
        value = int(raw)
    except ValueError:
        return get_context_budget()
    return value if value > 0 else get_context_budget()
