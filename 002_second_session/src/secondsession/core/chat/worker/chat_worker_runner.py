# 목적: 대화 워커 실행 스크립트를 제공한다.
# 설명: Redis 큐와 체크포인터를 구성해 워커를 실행한다.
# 디자인 패턴: 팩토리 메서드
# 참조: secondsession/core/chat/worker/chat_worker.py,
#       secondsession/core/common/checkpointer/redis_checkpointer.py

"""대화 워커 실행 모듈."""

from __future__ import annotations

import logging
import os

from secondsession.core.chat.worker.chat_worker import ChatWorker
from secondsession.core.common.app_config import AppConfig
from secondsession.core.common.checkpointer import InMemoryCheckpointer
from secondsession.core.common.queue import ChatJobQueue, ChatStreamEventQueue


class ChatWorkerRunner:
    """대화 워커 실행기."""

    def run(self) -> None:
        """워커를 실행한다."""
        os.makedirs("logs", exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
            handlers=[
                logging.FileHandler("logs/worker.log", encoding="utf-8"),
                logging.StreamHandler(),
            ],
        )
        config = AppConfig.from_env()
        redis_client = self._build_redis_client(config.redis_url)
        job_queue = ChatJobQueue(redis_client)
        event_queue = ChatStreamEventQueue(redis_client)
        checkpointer = InMemoryCheckpointer()
        worker = ChatWorker(
            job_queue=job_queue,
            event_queue=event_queue,
            checkpointer=checkpointer,
            redis_client=redis_client,
        )
        worker.run_forever()

    def _build_redis_client(self, redis_url: str | None):
        """Redis 클라이언트를 생성한다."""
        if not redis_url:
            raise ValueError("REDIS_URL 환경 변수가 필요합니다.")
        try:
            import redis
        except ImportError as exc:  # pragma: no cover - 환경 구성에 따라 달라짐
            raise RuntimeError("redis 패키지가 필요합니다.") from exc
        return redis.Redis.from_url(redis_url)


if __name__ == "__main__":
    runner = ChatWorkerRunner()
    runner.run()
