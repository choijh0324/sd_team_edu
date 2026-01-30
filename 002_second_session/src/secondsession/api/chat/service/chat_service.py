# 목적: 대화 서비스 인터페이스를 정의한다.
# 설명: 라우터가 호출할 서비스 메서드 시그니처를 제공한다.
# 디자인 패턴: 서비스 레이어
# 참조: secondsession/api/chat/router/chat_router.py

"""대화 서비스 인터페이스 모듈."""

from collections.abc import Iterable
import json
import os
import time
import uuid
from datetime import datetime

from secondsession.api.chat.model import (
    ChatJobRequest,
    ChatJobResponse,
    ChatJobStatusResponse,
    ChatJobCancelResponse,
)
from secondsession.api.chat.const import StreamEventType, MetadataEventType
from secondsession.core.common.queue import ChatJobQueue, ChatStreamEventQueue
from secondsession.core.chat.repository import ChatHistoryRepository

try:
    import redis
except ImportError:  # pragma: no cover - 환경 구성에 따라 달라짐
    redis = None


class ChatService:
    """대화 서비스 인터페이스."""

    def __init__(self) -> None:
        """서비스 의존성을 초기화한다."""
        if redis is None:
            raise RuntimeError("redis 패키지가 필요합니다. 의존성을 설치해 주세요.")
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis_client = redis.Redis.from_url(redis_url)
        self._job_queue = ChatJobQueue(redis_client)
        self._event_queue = ChatStreamEventQueue(redis_client)
        self._history_repo = ChatHistoryRepository(redis_client)

    def create_job(self, request: ChatJobRequest) -> ChatJobResponse:
        """대화 작업을 생성한다.

        TODO:
            - job_id/trace_id 생성
            - 워커 큐에 작업 적재
            - 대화 요청 → 스트리밍 응답 → 5턴 초과 시 요약 플로우를 설계
            - thread_id 기반 복구 로직을 연결
            - 체크포인터에 thread_id를 전달해 대화 내역을 복구
            - safeguard 분기 결과를 error_code/metadata에 기록
            - 폴백 케이스에서도 스트리밍 이벤트를 정상 종료
        """
        job_id = f"job-{uuid.uuid4().hex}"
        trace_id = f"trace-{uuid.uuid4().hex}"
        thread_id = request.thread_id or f"thread-{uuid.uuid4().hex}"

        payload = {
            "job_id": job_id,
            "trace_id": trace_id,
            "thread_id": thread_id,
            "query": request.query,
            "history": request.history or [],
            "turn_count": request.turn_count or 0,
            "checkpoint_id": request.checkpoint_id,
            "user_id": request.user_id,
            "metadata": request.metadata,
        }
        self._job_queue.enqueue(payload)
        if request.user_id:
            for item in request.history or []:
                self._history_repo.append_item(request.user_id, thread_id, item)
        self._event_queue.push_event(job_id, {
            "type": StreamEventType.METADATA.value,
            "content": json.dumps({
                "event": MetadataEventType.JOB_QUEUED.value,
                "message": "작업이 큐에 적재됨",
                "timestamp": datetime.utcnow().isoformat(),
                "node": "api",
                "route": None,
                "error_code": None,
                "safeguard_label": None,
            }, ensure_ascii=False),
            "node": "api",
            "trace_id": trace_id,
            "seq": 1,
        })

        return ChatJobResponse(
            job_id=job_id,
            trace_id=trace_id,
            thread_id=thread_id,
        )

    def stream_events(self, job_id: str) -> Iterable[str]:
        """스트리밍 이벤트를 SSE 라인으로 반환한다.

        TODO:
            - Redis에서 이벤트를 소비
            - done 이벤트까지 전송
            - 대화 응답 토큰과 메타데이터를 순서대로 전달
            - seq는 job_id 기준으로 단조 증가하도록 구성
            - type/token/metadata/error/done 포맷을 유지
            - 종료 시 done 이벤트를 반드시 적재
            - 폴백 에러 코드가 있는 경우 error 이벤트를 먼저 전송
        """
        while True:
            event = self._event_queue.pop_event(job_id)
            if event is None:
                time.sleep(0.1)
                continue
            yield self._to_sse_line(event)
            if event.get("type") == "done":
                break

    def get_status(self, job_id: str) -> ChatJobStatusResponse:
        """작업 상태를 조회한다.

        TODO:
            - 상태 저장소 조회
            - 진행률/상태 반환
        """
        last_seq = self._event_queue.get_last_seq(job_id)
        status = "completed" if last_seq > 0 else "pending"
        return ChatJobStatusResponse(
            job_id=job_id,
            status=status,
            last_seq=last_seq if last_seq > 0 else None,
        )

    def cancel(self, job_id: str) -> ChatJobCancelResponse:
        """작업을 취소한다.

        TODO:
            - 취소 플래그 기록
            - 워커가 취소를 확인하도록 구성
        """
        cancel_key = f"chat:cancel:{job_id}"
        self._job_queue._redis.set(cancel_key, "1")
        return ChatJobCancelResponse(job_id=job_id, status="cancelled")

    def _to_sse_line(self, event: dict) -> str:
        """SSE 데이터 라인을 생성한다."""
        payload = json.dumps(event, ensure_ascii=False)
        return f"data: {payload}\n\n"
