# 목적: 주택 작업 서비스 레이어를 정의한다.
# 설명: 작업 생성/취소/상태 조회/스트림 조회를 담당한다.
# 디자인 패턴: 애플리케이션 서비스 패턴
# 참조: fourthsession/core/common/queue

"""주택 작업 서비스 모듈."""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from uuid import uuid4

from fourthsession.api.housing_agent.model.job_cancel_response import (
    HousingJobCancelResponse,
)
from fourthsession.api.housing_agent.model.job_request import HousingJobRequest
from fourthsession.api.housing_agent.model.job_response import HousingJobResponse
from fourthsession.api.housing_agent.model.job_status_response import (
    HousingJobStatusResponse,
)
from fourthsession.api.housing_agent.model.job_stream_response import (
    HousingJobStreamResponse,
)
from fourthsession.core.common.queue.inmemory_job_store import InMemoryJobStore
from fourthsession.core.common.queue.job_queue import RedisJobQueue
from fourthsession.core.common.queue.stream_event_queue import RedisStreamEventQueue


LOGGER = logging.getLogger(__name__)


class HousingJobService:
    """주택 작업 서비스."""

    def __init__(
        self,
        job_queue: RedisJobQueue | None = None,
        stream_queue: RedisStreamEventQueue | None = None,
        job_store: InMemoryJobStore | None = None,
    ) -> None:
        """서비스 의존성을 초기화한다.

        Args:
            job_queue (RedisJobQueue | None): 작업 큐.
            stream_queue (RedisStreamEventQueue | None): 스트림 이벤트 큐.
            job_store (InMemoryJobStore | None): 작업 상태 저장소.
        """
        self._job_queue = job_queue
        self._stream_queue = stream_queue
        self._job_store = job_store

        if self._job_queue is None:
            try:
                self._job_queue = RedisJobQueue()
            except NotImplementedError:
                LOGGER.info("RedisJobQueue가 미구현 상태라 비활성화합니다.")
            except Exception:
                LOGGER.exception("RedisJobQueue 초기화에 실패했습니다.")

        if self._stream_queue is None:
            try:
                self._stream_queue = RedisStreamEventQueue()
            except NotImplementedError:
                LOGGER.info("RedisStreamEventQueue가 미구현 상태라 비활성화합니다.")
            except Exception:
                LOGGER.exception("RedisStreamEventQueue 초기화에 실패했습니다.")

        if self._job_store is None:
            try:
                self._job_store = InMemoryJobStore()
            except NotImplementedError:
                LOGGER.info("InMemoryJobStore가 미구현 상태라 비활성화합니다.")
            except Exception:
                LOGGER.exception("InMemoryJobStore 초기화에 실패했습니다.")

    def create_job(self, request: HousingJobRequest) -> HousingJobResponse:
        """작업을 생성한다.

        Args:
            request (HousingJobRequest): 작업 생성 요청.

        Returns:
            HousingJobResponse: 작업 생성 응답.
        """
        job_id = str(uuid4())
        trace_id = request.trace_id or str(uuid4())
        payload = request.model_dump(exclude_none=True)
        payload["job_id"] = job_id
        payload["trace_id"] = trace_id

        status = "QUEUED"
        if self._job_store is not None:
            try:
                self._job_store.create(job_id=job_id, payload=payload)
            except Exception:
                LOGGER.exception("작업 저장소 저장에 실패했습니다: job_id=%s", job_id)
                status = "FAILED"

        if status != "FAILED" and self._job_queue is not None:
            try:
                self._job_queue.enqueue(payload)
            except Exception:
                LOGGER.exception("작업 큐 적재에 실패했습니다: job_id=%s", job_id)
                status = "FAILED"

        if self._job_store is not None and status == "FAILED":
            try:
                self._job_store.update_status(job_id=job_id, status="FAILED")
            except Exception:
                LOGGER.exception("작업 실패 상태 반영에 실패했습니다: job_id=%s", job_id)

        return HousingJobResponse(job_id=job_id, status=status, trace_id=trace_id)

    def cancel_job(self, job_id: str) -> HousingJobCancelResponse:
        """작업을 취소한다.

        Args:
            job_id (str): 작업 식별자.

        Returns:
            HousingJobCancelResponse: 취소 응답.
        """
        if self._job_store is None:
            return HousingJobCancelResponse(job_id=job_id, status="NOT_FOUND")

        job = self._job_store.get(job_id)
        if job is None:
            return HousingJobCancelResponse(job_id=job_id, status="NOT_FOUND")

        if job.status in {"COMPLETED", "FAILED", "CANCELLED"}:
            return HousingJobCancelResponse(job_id=job_id, status=job.status)

        updated = self._job_store.update_status(job_id=job_id, status="CANCELLED")
        if updated is None:
            return HousingJobCancelResponse(job_id=job_id, status="NOT_FOUND")

        if self._stream_queue is not None:
            try:
                self._stream_queue.push_event(
                    job_id=job_id,
                    event={
                        "type": "status",
                        "status": "CANCELLED",
                        "updated_at": datetime.now(UTC).isoformat(),
                    },
                )
            except Exception:
                LOGGER.exception("취소 이벤트 적재에 실패했습니다: job_id=%s", job_id)

        return HousingJobCancelResponse(job_id=job_id, status=updated.status)

    def get_status(self, job_id: str) -> HousingJobStatusResponse:
        """작업 상태를 조회한다.

        Args:
            job_id (str): 작업 식별자.

        Returns:
            HousingJobStatusResponse: 상태 응답.
        """
        if self._job_store is None:
            return HousingJobStatusResponse(job_id=job_id, status="NOT_FOUND", updated_at=None)

        job = self._job_store.get(job_id)
        if job is None:
            return HousingJobStatusResponse(job_id=job_id, status="NOT_FOUND", updated_at=None)

        return HousingJobStatusResponse(
            job_id=job.job_id,
            status=job.status,
            updated_at=job.updated_at,
        )

    def stream(self, job_id: str) -> HousingJobStreamResponse:
        """스트림 이벤트를 조회한다.

        Args:
            job_id (str): 작업 식별자.

        Returns:
            HousingJobStreamResponse: 스트림 응답.
        """
        if self._stream_queue is None:
            return HousingJobStreamResponse(job_id=job_id, event=None, empty=True)

        try:
            event = self._stream_queue.pop_event(job_id)
        except Exception:
            LOGGER.exception("스트림 이벤트 조회에 실패했습니다: job_id=%s", job_id)
            return HousingJobStreamResponse(job_id=job_id, event=None, empty=True)

        return HousingJobStreamResponse(job_id=job_id, event=event, empty=event is None)
