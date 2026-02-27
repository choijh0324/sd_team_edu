# 목적: 주택 작업 워커를 정의한다.
# 설명: Redis 작업 큐를 소비해 에이전트 실행 결과를 상태/스트림에 반영한다.
# 디자인 패턴: 템플릿 메서드 패턴(WorkerBase 상속)
# 참조: fourthsession/core/common/worker/worker_base.py, fourthsession/api/housing_agent/service

"""주택 작업 워커 모듈."""

from __future__ import annotations

from datetime import UTC, datetime
import logging

from fourthsession.api.housing_agent.model.request import HousingAgentRequest
from fourthsession.api.housing_agent.service.housing_agent_service import (
    HousingAgentService,
)
from fourthsession.core.common.queue.inmemory_job_store import InMemoryJobStore
from fourthsession.core.common.queue.job_queue import RedisJobQueue
from fourthsession.core.common.queue.stream_event_queue import RedisStreamEventQueue
from fourthsession.core.common.worker.worker_base import WorkerBase


LOGGER = logging.getLogger(__name__)


class HousingJobWorker(WorkerBase):
    """주택 작업 워커."""

    def __init__(
        self,
        job_queue: RedisJobQueue,
        job_store: InMemoryJobStore,
        stream_queue: RedisStreamEventQueue,
        agent_service: HousingAgentService,
        poll_interval: float = 1.0,
    ) -> None:
        """워커 의존성을 초기화한다.

        Args:
            job_queue (RedisJobQueue): 작업 큐.
            job_store (InMemoryJobStore): 작업 상태 저장소.
            stream_queue (RedisStreamEventQueue): 스트림 이벤트 큐.
            agent_service (HousingAgentService): 에이전트 서비스.
            poll_interval (float): 폴링 간격(초).
        """
        super().__init__(poll_interval=poll_interval)
        self._job_queue = job_queue
        self._job_store = job_store
        self._stream_queue = stream_queue
        self._agent_service = agent_service

    def run_once(self) -> bool:
        """작업을 한 번 처리한다."""
        payload = self._job_queue.dequeue()
        if payload is None:
            return False

        job_id = str(payload.get("job_id", ""))
        trace_id = payload.get("trace_id")
        if not job_id:
            LOGGER.warning("job_id가 없는 payload를 건너뜁니다: payload=%s", payload)
            return True

        try:
            self._job_store.update_status(job_id=job_id, status="RUNNING")
            self._stream_queue.push_event(
                job_id=job_id,
                event={
                    "type": "status",
                    "status": "RUNNING",
                    "updated_at": datetime.now(UTC).isoformat(),
                },
            )

            request = HousingAgentRequest.from_payload(payload)
            response = self._agent_service.handle(request)

            self._job_store.update_status(job_id=job_id, status="COMPLETED")
            self._stream_queue.push_event(
                job_id=job_id,
                event={
                    "type": "result",
                    "status": "COMPLETED",
                    "trace_id": response.trace_id or trace_id,
                    "answer": response.answer,
                    "metadata": response.metadata,
                    "updated_at": datetime.now(UTC).isoformat(),
                },
            )
        except Exception:
            LOGGER.exception("작업 처리에 실패했습니다: job_id=%s", job_id)
            self._job_store.update_status(job_id=job_id, status="FAILED")
            self._stream_queue.push_event(
                job_id=job_id,
                event={
                    "type": "error",
                    "status": "FAILED",
                    "message": "작업 처리 중 오류가 발생했습니다.",
                    "updated_at": datetime.now(UTC).isoformat(),
                },
            )
        return True
