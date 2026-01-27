# 목적: 대화 API 라우터를 제공한다.
# 설명: 작업 생성/스트리밍/상태/취소 엔드포인트를 정의한다.
# 디자인 패턴: 라우터
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

router = APIRouter(prefix="/chat", tags=["chat"])
service = ChatService()


@router.post("/jobs", response_model=ChatJobResponse)
def create_chat_job(payload: ChatJobRequest) -> ChatJobResponse:
    """대화 작업을 생성한다."""
    return service.create_job(payload)


@router.get("/stream/{job_id}")
def stream_chat(job_id: str) -> StreamingResponse:
    """대화 스트리밍 엔드포인트."""
    return StreamingResponse(
        service.stream_events(job_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/status/{job_id}", response_model=ChatJobStatusResponse)
def get_chat_status(job_id: str) -> ChatJobStatusResponse:
    """대화 작업 상태를 조회한다."""
    return service.get_status(job_id)


@router.post("/cancel/{job_id}", response_model=ChatJobCancelResponse)
def cancel_chat_job(job_id: str) -> ChatJobCancelResponse:
    """대화 작업을 취소한다."""
    return service.cancel(job_id)
