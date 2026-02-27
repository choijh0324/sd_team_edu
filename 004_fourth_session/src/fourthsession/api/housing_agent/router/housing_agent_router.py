# 목적: 주택 에이전트 라우터를 정의한다.
# 설명: API 엔드포인트와 서비스 호출을 연결한다.
# 디자인 패턴: 라우터 패턴
# 참조: fourthsession/api/housing_agent/service

"""주택 에이전트 라우터 모듈."""

from fastapi import APIRouter

from fourthsession.api.housing_agent.const.api_constants import HousingApiConstants
from fourthsession.api.housing_agent.model.request import HousingAgentRequest
from fourthsession.api.housing_agent.model.response import HousingAgentResponse
from fourthsession.api.housing_agent.service.housing_agent_service import (
    HousingAgentService,
)


class HousingAgentRouter:
    """주택 에이전트 라우터."""

    def __init__(self, service: HousingAgentService) -> None:
        """라우터를 초기화한다.

        Args:
            service (HousingAgentService): 주택 에이전트 서비스.
        """
        self._service = service

    def build(self) -> APIRouter:
        """라우터를 생성해 반환한다.

        Returns:
            APIRouter: 구성된 라우터.
        """
        constants = HousingApiConstants()
        router = APIRouter(prefix=constants.api_prefix, tags=[constants.tag])
        router.add_api_route(
            path=constants.agent_path,
            endpoint=self.agent,
            methods=["POST"],
            response_model=HousingAgentResponse,
        )
        return router

    def agent(self, request: HousingAgentRequest) -> HousingAgentResponse:
        """주택 에이전트 요청을 처리한다.

        Args:
            request (HousingAgentRequest): 주택 에이전트 요청 모델.

        Returns:
            HousingAgentResponse: 주택 에이전트 응답 모델.
        """
        return self._service.handle(request)
