# 목적: 프로젝트 전역 SSE 직렬화 유틸리티를 제공한다.
# 설명: SSE data 라인 생성/파싱과 DONE 이벤트 생성을 공통 처리한다.
# 디자인 패턴: Utility
# 참조: thirdsession/api/rag/service/stream_utils.py

"""SSE 공통 유틸리티 모듈."""

from __future__ import annotations

import json
from typing import Any


def to_sse_line(payload: dict[str, Any]) -> str:
    """payload를 SSE data 라인으로 직렬화한다."""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def parse_sse_line(line: str) -> dict[str, Any] | None:
    """SSE data 라인에서 JSON payload를 추출한다."""
    prefix = "data: "
    stripped = line.strip()
    if not stripped.startswith(prefix):
        return None
    raw = stripped[len(prefix) :]
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def done_sse_line() -> str:
    """표준 DONE SSE 라인을 반환한다."""
    return to_sse_line({"type": "DONE"})
