# 목적: Redis 기반 체크포인터 생성 함수를 제공한다.
# 설명: LangGraph 체크포인터를 Redis로 구성하는 진입점이다.
# 디자인 패턴: 팩토리 메서드
# 참조: secondsession/core/chat/graphs/chat_graph.py

"""Redis 체크포인터 팩토리 모듈."""

import importlib


def build_redis_checkpointer(redis_url: str) -> object:
    """Redis 체크포인터를 생성한다.

    TODO:
        - langgraph-checkpoint-redis 패키지의 클래스를 확인한다.
        - Redis 연결 정보를 주입해 체크포인터를 반환한다.
        - 비동기 사용 시 asyncio 환경을 고려한다.
        - metadata에 node/route/error_code/safeguard_label을 저장하는 규칙을 정의한다.
    """
    candidates: list[tuple[str, str]] = [
        ("langgraph.checkpoint.redis", "RedisCheckpointSaver"),
        ("langgraph.checkpoint.redis", "RedisCheckpoint"),
        ("langgraph.checkpoint.redis", "RedisCheckpointer"),
        ("langgraph.checkpoint.redis", "RedisSaver"),
    ]
    for module_name, class_name in candidates:
        module = _safe_import(module_name)
        if module is None:
            continue
        cls = getattr(module, class_name, None)
        if cls is None:
            continue
        return _instantiate(cls, redis_url)
    raise RuntimeError(
        "Redis 체크포인터 클래스를 찾을 수 없습니다. "
        "langgraph-checkpoint-redis 설치 여부를 확인해 주세요."
    )


def _safe_import(module_name: str):
    """모듈을 안전하게 임포트한다."""
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None


def _instantiate(cls, redis_url: str) -> object:
    """클래스를 redis_url로 생성한다."""
    try:
        return cls(redis_url=redis_url)
    except TypeError:
        return cls(redis_url)
