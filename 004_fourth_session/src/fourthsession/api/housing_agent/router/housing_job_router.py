# 목적: 주택 작업 생성 라우터를 정의한다.
# 설명: 작업 생성 요청을 서비스로 전달한다.
# 디자인 패턴: 라우터 패턴
# 참조: fourthsession/api/housing_agent/service/housing_job_service.py

"""주택 작업 생성 라우터 모듈."""

from fastapi import APIRouter

from fourthsession.api.housing_agent.const.api_constants import HousingApiConstants
from fourthsession.api.housing_agent.model.job_request import HousingJobRequest
from fourthsession.api.housing_agent.model.job_response import HousingJobResponse
from fourthsession.api.housing_agent.service.housing_job_service import HousingJobService


class HousingJobRouter:
    """주택 작업 생성 라우터."""

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
            path=constants.job_path,
            endpoint=self.create_job,
            methods=["POST"],
            response_model=HousingJobResponse,
        )
        return router

    def create_job(self, request: HousingJobRequest) -> HousingJobResponse:
        """주택 작업 생성 요청을 처리한다.

        Args:
            request (HousingJobRequest): 작업 생성 요청 모델.

        Returns:
            HousingJobResponse: 작업 생성 응답 모델.
        """
        return self._service.create_job(request)
