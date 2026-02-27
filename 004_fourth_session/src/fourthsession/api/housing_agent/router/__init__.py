# 목적: 주택 에이전트 라우터 등록 함수를 제공한다.
# 설명: app.state에 있는 서비스 객체를 사용해 라우터를 등록한다.
# 디자인 패턴: 레지스트리 패턴
# 참조: fourthsession/api/housing_agent/router/*

"""주택 에이전트 라우터 등록 모듈."""

from fastapi import FastAPI

from fourthsession.api.housing_agent.router.housing_agent_router import HousingAgentRouter
from fourthsession.api.housing_agent.router.housing_cancel_router import (
    HousingJobCancelRouter,
)
from fourthsession.api.housing_agent.router.housing_job_router import HousingJobRouter
from fourthsession.api.housing_agent.router.housing_status_router import (
    HousingJobStatusRouter,
)
from fourthsession.api.housing_agent.router.housing_stream_router import (
    HousingJobStreamRouter,
)


def register_routes(app: FastAPI) -> None:
    """주택 에이전트 라우터를 앱에 등록한다.

    Args:
        app (FastAPI): FastAPI 애플리케이션.
    """
    agent_service = (
        getattr(app.state, "housing_agent_service", None)
        or getattr(app.state, "agent_service", None)
    )
    if agent_service is None:
        raise RuntimeError("app.state에 housing_agent_service가 없습니다.")

    job_service = (
        getattr(app.state, "housing_job_service", None)
        or getattr(app.state, "job_service", None)
    )
    if job_service is None:
        raise RuntimeError("app.state에 housing_job_service가 없습니다.")

    app.include_router(HousingAgentRouter(agent_service).build())
    app.include_router(HousingJobRouter(job_service).build())
    app.include_router(HousingJobCancelRouter(job_service).build())
    app.include_router(HousingJobStatusRouter(job_service).build())
    app.include_router(HousingJobStreamRouter(job_service).build())


__all__ = ["register_routes"]
