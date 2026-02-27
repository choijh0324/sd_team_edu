# 목적: 주택 작업 스트림 라우터를 정의한다.
# 설명: 스트림 이벤트를 조회한다.
# 디자인 패턴: 라우터 패턴
# 참조: fourthsession/api/housing_agent/service/housing_job_service.py

"""주택 작업 스트림 라우터 모듈."""

from fastapi import APIRouter

from fourthsession.api.housing_agent.const.api_constants import HousingApiConstants
from fourthsession.api.housing_agent.model.job_stream_response import (
    HousingJobStreamResponse,
)
from fourthsession.api.housing_agent.service.housing_job_service import HousingJobService


class HousingJobStreamRouter:
    """주택 작업 스트림 라우터."""

    def __init__(self, service: HousingJobService) -> None:
        """라우터를 초기화한다.

        Args:
            service (HousingJobService): 작업 서비스.
        """
        self._service = service

    def build(self) -> APIRouter:
        """라우터를 생성해 반환한다.

        Returns:
            APIRouter: 구성된 라우터.
        """
        constants = HousingApiConstants()
        router = APIRouter(prefix=constants.api_prefix, tags=[constants.job_tag])
        router.add_api_route(
            path=constants.job_stream_path,
            endpoint=self.stream,
            methods=["GET"],
            response_model=HousingJobStreamResponse,
        )
        return router

    def stream(self, job_id: str) -> HousingJobStreamResponse:
        """주택 작업 스트림 조회 요청을 처리한다.

        Args:
            job_id (str): 작업 식별자.

        Returns:
            HousingJobStreamResponse: 스트림 이벤트 응답.
        """
        return self._service.stream(job_id)
