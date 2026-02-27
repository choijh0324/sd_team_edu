# 목적: FastAPI 애플리케이션 진입점을 제공한다.
# 설명: uvicorn에서 "fourthsession.main:app" 형태로 실행할 수 있는 앱 객체를 정의한다.
# 디자인 패턴: 팩토리 메서드 패턴(애플리케이션 생성 책임 분리)
# 참조: fourthsession/api, fourthsession/core

"""FastAPI 애플리케이션 진입점 모듈."""

from threading import Thread

from fastapi import FastAPI

from fourthsession.api.housing_agent.router import register_routes
from fourthsession.api.housing_agent.service.housing_agent_service import (
    HousingAgentService,
)
from fourthsession.api.housing_agent.service.housing_job_service import HousingJobService
from fourthsession.core.common.logging_config import configure_logging
from fourthsession.core.common.queue.inmemory_job_store import InMemoryJobStore
from fourthsession.core.common.queue.job_queue import RedisJobQueue
from fourthsession.core.common.queue.stream_event_queue import RedisStreamEventQueue
from fourthsession.core.common.worker.housing_job_worker import HousingJobWorker


def create_app() -> FastAPI:
    """FastAPI 애플리케이션을 생성한다.

    Returns:
        FastAPI: 구성된 애플리케이션 인스턴스.
    """
    configure_logging(service_name="fourthsession-api")
    app = FastAPI(title="fourthSession API")

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        """간단한 헬스 체크 엔드포인트."""
        return {"status": "ok"}

    job_queue = RedisJobQueue()
    stream_queue = RedisStreamEventQueue()
    job_store = InMemoryJobStore()

    housing_agent_service = HousingAgentService()
    housing_job_service = HousingJobService(
        job_queue=job_queue,
        stream_queue=stream_queue,
        job_store=job_store,
    )
    housing_job_worker = HousingJobWorker(
        job_queue=job_queue,
        stream_queue=stream_queue,
        job_store=job_store,
        agent_service=housing_agent_service,
        poll_interval=1.0,
    )

    app.state.housing_agent_service = housing_agent_service
    app.state.housing_job_service = housing_job_service
    app.state.housing_job_worker = housing_job_worker
    app.state.housing_job_worker_thread = Thread(
        target=housing_job_worker.run,
        name="housing-job-worker",
        daemon=True,
    )
    register_routes(app)

    @app.on_event("startup")
    def startup_worker() -> None:
        """앱 시작 시 백그라운드 워커를 시작한다."""
        worker_thread = app.state.housing_job_worker_thread
        if not worker_thread.is_alive():
            worker_thread.start()

    @app.on_event("shutdown")
    def shutdown_worker() -> None:
        """앱 종료 시 워커를 중지한다."""
        worker = app.state.housing_job_worker
        worker.stop()

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("fourthsession.main:app", host="0.0.0.0", port=8000, reload=True)
