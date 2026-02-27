# 목적: 인메모리 작업 저장소를 정의한다.
# 설명: 작업 상태를 프로세스 메모리에 저장한다.
# 디자인 패턴: 리포지토리 패턴
# 참조: fourthsession/core/common/queue/job_record.py

"""인메모리 작업 저장소 모듈."""

from __future__ import annotations

from datetime import UTC, datetime
from threading import Lock

from fourthsession.core.common.queue.job_record import JobRecord


class InMemoryJobStore:
    """인메모리 작업 저장소."""

    def __init__(self) -> None:
        """저장소를 초기화한다."""
        self._records: dict[str, JobRecord] = {}
        self._lock = Lock()

    def create(self, job_id: str, payload: dict) -> JobRecord:
        """작업 레코드를 생성한다.

        Args:
            job_id (str): 작업 식별자.
            payload (dict): 작업 페이로드.

        Returns:
            JobRecord: 생성된 레코드.
        """
        timestamp = datetime.now(UTC).isoformat()
        record = JobRecord(
            job_id=job_id,
            status="QUEUED",
            payload=dict(payload),
            created_at=timestamp,
            updated_at=timestamp,
        )
        with self._lock:
            self._records[job_id] = record
        return record

    def update_status(self, job_id: str, status: str) -> JobRecord | None:
        """작업 상태를 갱신한다.

        Args:
            job_id (str): 작업 식별자.
            status (str): 변경 상태.

        Returns:
            JobRecord | None: 갱신된 레코드.
        """
        with self._lock:
            record = self._records.get(job_id)
            if record is None:
                return None
            record.status = status
            record.updated_at = datetime.now(UTC).isoformat()
            return record

    def get(self, job_id: str) -> JobRecord | None:
        """작업 레코드를 조회한다.

        Args:
            job_id (str): 작업 식별자.

        Returns:
            JobRecord | None: 작업 레코드.
        """
        with self._lock:
            return self._records.get(job_id)
