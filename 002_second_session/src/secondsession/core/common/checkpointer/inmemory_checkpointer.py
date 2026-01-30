# 목적: LangGraph 인메모리 체크포인터를 제공한다.
# 설명: LangGraph의 InMemorySaver를 프로젝트에서 쓰는 이름으로 감싼다.
# 디자인 패턴: 어댑터
# 참조: docs/03_langgraph_checkpoint/03_인메모리_체크포인터.md

"""인메모리 체크포인터 모듈."""

from __future__ import annotations

try:
    from langgraph.checkpoint.memory import InMemorySaver
except ImportError as exc:  # pragma: no cover - 환경 구성에 따라 달라짐
    raise RuntimeError(
        "langgraph.checkpoint.memory의 InMemorySaver를 불러올 수 없습니다."
    ) from exc


class InMemoryCheckpointer(InMemorySaver):
    """LangGraph 인메모리 체크포인터 래퍼."""
