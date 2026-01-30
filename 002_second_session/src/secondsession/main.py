# 목적: FastAPI 애플리케이션 진입점을 제공한다.
# 설명: uvicorn에서 \"secondsession.main:app\" 형태로 실행할 수 있는 앱 객체를 정의한다.
# 디자인 패턴: 팩토리 메서드 패턴(애플리케이션 생성 책임 분리)
# 참조: secondsession/api, secondsession/core

"""FastAPI 애플리케이션 진입점 모듈."""

from fastapi import FastAPI

from secondsession.core.common.checkpointer import build_redis_checkpointer
from secondsession.core.common.queue import ChatJobQueue, ChatStreamEventQueue

from secondsession.api.chat.router.chat_router import ChatRouter
from secondsession.api.chat.service.chat_service import ChatService
from secondsession.core.chat.graphs.chat_graph import ChatGraph
from secondsession.core.common.app_config import AppConfig
from secondsession.core.common.llm_client import LlmClient


def _build_redis_client(redis_url: str | None):
    """Redis 클라이언트를 생성한다."""
    if not redis_url:
        raise ValueError("REDIS_URL 환경 변수가 필요합니다.")
    try:
        import redis
    except ImportError as exc:  # pragma: no cover - 환경 구성에 따라 달라짐
        raise RuntimeError("redis 패키지가 필요합니다.") from exc
    return redis.Redis.from_url(redis_url)


def create_app() -> FastAPI:
    """FastAPI 애플리케이션을 생성한다.

    Returns:
        FastAPI: 구성된 애플리케이션 인스턴스.
    """
    app = FastAPI(title="secondsession API")

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        """간단한 헬스 체크 엔드포인트."""
        return {"status": "ok"}

    config = AppConfig.from_env()
    redis_client = _build_redis_client(config.redis_url)
    job_queue = ChatJobQueue(redis_client)
    event_queue = ChatStreamEventQueue(redis_client)
    checkpointer = build_redis_checkpointer(config.redis_url)
    llm_client = LlmClient(config)
    graph = ChatGraph(checkpointer=checkpointer, llm_client=llm_client)
    service = ChatService(
        graph,
        job_queue=job_queue,
        event_queue=event_queue,
        redis_client=redis_client,
    )
    chat_router = ChatRouter(service)
    app.include_router(chat_router.router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("secondsession.main:app", host="0.0.0.0", port=8000, reload=True)
