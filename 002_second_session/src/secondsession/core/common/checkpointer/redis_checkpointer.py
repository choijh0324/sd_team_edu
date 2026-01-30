# 목적: Redis 기반 체크포인터 생성 함수를 제공한다.
# 설명: LangGraph 체크포인터를 Redis로 구성하는 진입점이다.
# 디자인 패턴: 팩토리 메서드
# 참조: secondsession/core/chat/graphs/chat_graph.py

"""Redis 체크포인터 팩토리 모듈."""

from __future__ import annotations

import importlib

from typing import Any


def build_redis_checkpointer(redis_url: str) -> object:
    """Redis 체크포인터를 생성한다.

    구현 내용:
        - langgraph-checkpoint-redis 패키지의 클래스를 탐색한다.
        - Redis 연결 정보를 주입해 체크포인터를 반환한다.
        - metadata 저장 규칙(하단 주석)을 따른다.
    """
    if not redis_url:
        raise ValueError("redis_url이 필요합니다.")

    candidates: list[tuple[str, str]] = [
        ("langgraph.checkpoint.redis", "RedisCheckpointSaver"),
        ("langgraph.checkpoint.redis", "RedisCheckpointer"),
        ("langgraph.checkpoint.redis", "RedisCheckpoint"),
        ("langgraph.checkpoint.redis", "RedisSaver"),
    ]
    for module_name, class_name in candidates:
        cls = _load_class(module_name, class_name)
        if cls is None:
            continue
        return _instantiate(cls, redis_url)
    raise RuntimeError(
        "Redis 체크포인터 클래스를 찾을 수 없습니다. "
        "langgraph-checkpoint-redis 설치 여부를 확인해 주세요."
    )


def _load_class(module_name: str, class_name: str) -> type | None:
    """모듈에서 클래스를 안전하게 로딩한다."""
    try:
        module = importlib.import_module(module_name)
    except ImportError:
        return None
    return getattr(module, class_name, None)


def _instantiate(cls: type, redis_url: str) -> Any:
    """클래스를 redis_url로 생성한다."""
    try:
        return cls(redis_url=redis_url)
    except TypeError:
        try:
            return cls(url=redis_url)
        except TypeError:
            return cls(redis_url)


# 메타데이터 저장 규칙(기본):
# - node: 현재 노드 이름
# - route: 라우팅 결과
# - error_code: 에러 코드 문자열
# - safeguard_label: 안전 라벨 문자열
