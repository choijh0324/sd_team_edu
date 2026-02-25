# 목적: 비동기 워커의 실행 뼈대를 정의한다.
# 설명: 비동기 작업 루프의 공통 흐름을 고정하고 하위 클래스가 세부 구현을 제공한다.
# 디자인 패턴: 템플릿 메서드 패턴
# 참조: nextStep.md

"""비동기 워커 베이스 모듈."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any


class AsyncWorkerBase(ABC):
    """비동기 워커 베이스 클래스."""

    def __init__(self, poll_interval: float = 0.1) -> None:
        """비동기 워커를 초기화한다.

        Args:
            poll_interval: 작업 폴링 간격(초).
        """
        self._poll_interval = poll_interval
        self._stop_requested = False

    def stop(self) -> None:
        """비동기 워커 종료를 요청한다."""
        self._stop_requested = True

    async def run_forever(self) -> None:
        """비동기 작업 루프를 실행한다.

        구현 내용:
            - stop 플래그 기반 종료
            - 큐가 비면 poll_interval 만큼 비동기 대기
            - 예외 발생 시 간단 백오프 후 루프 지속
        """
        while not self._stop_requested:
            try:
                job = await self.fetch_job()
                if job is None:
                    await asyncio.sleep(self._poll_interval)
                    continue
                await self.handle_job(job)
            except Exception:
                await asyncio.sleep(min(self._poll_interval * 2, 1.0))

    @abstractmethod
    async def fetch_job(self) -> dict[str, Any] | None:
        """작업을 비동기로 가져온다.

        Returns:
            dict[str, Any] | None: 작업 페이로드 또는 None.
        """

    @abstractmethod
    async def handle_job(self, payload: dict[str, Any]) -> None:
        """작업을 비동기로 처리한다.

        Args:
            payload: 작업 페이로드.
        """
        _ = payload
