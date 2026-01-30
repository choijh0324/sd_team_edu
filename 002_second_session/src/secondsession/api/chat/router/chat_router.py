# 목적: 대화 API 라우터를 제공한다.
# 설명: 작업 생성/스트리밍/상태/취소 엔드포인트를 정의한다.
# 디자인 패턴: 라우터 팩토리 패턴
# 참조: secondsession/api/chat/service/chat_service.py

"""대화 API 라우터 모듈."""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from secondsession.api.chat.model import (
    ChatJobRequest,
    ChatJobResponse,
    ChatJobStatusResponse,
    ChatJobCancelResponse,
)
from secondsession.api.chat.service import ChatService


class ChatRouter:
    """대화 API 라우터를 구성한다."""

    def __init__(self, service: ChatService) -> None:
        """라우터와 의존성을 초기화한다.

        Args:
            service: 대화 서비스.
        """
        self._service = service
        self.router = APIRouter(prefix="/chat", tags=["chat"])
        self._register_routes()

    def _register_routes(self) -> None:
        """라우트 등록을 수행한다."""
        self.router.add_api_route(
            "/jobs",
            self.create_chat_job,
            methods=["POST"],
            response_model=ChatJobResponse,
        )
        self.router.add_api_route(
            "/stream/{job_id}",
            self.stream_chat,
            methods=["GET"],
        )
        self.router.add_api_route(
            "/status/{job_id}",
            self.get_chat_status,
            methods=["GET"],
            response_model=ChatJobStatusResponse,
        )
        self.router.add_api_route(
            "/cancel/{job_id}",
            self.cancel_chat_job,
            methods=["POST"],
            response_model=ChatJobCancelResponse,
        )

    def create_chat_job(self, payload: ChatJobRequest) -> ChatJobResponse:
        """대화 작업을 생성한다."""
        return self._service.create_job(payload)

    def stream_chat(self, job_id: str) -> StreamingResponse:
        """대화 스트리밍 엔드포인트."""
        return StreamingResponse(
            self._service.stream_events(job_id),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )

    def get_chat_status(self, job_id: str) -> ChatJobStatusResponse:
        """대화 작업 상태를 조회한다."""
        return self._service.get_status(job_id)

    def cancel_chat_job(self, job_id: str) -> ChatJobCancelResponse:
        """대화 작업을 취소한다."""
        return self._service.cancel(job_id)
