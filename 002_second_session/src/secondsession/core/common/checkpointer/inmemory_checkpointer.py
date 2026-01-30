# 목적: 인메모리 체크포인터를 제공한다.
# 설명: thread_id 기준으로 상태 스냅샷을 저장/복구한다.
# 디자인 패턴: Repository, Memento
# 참조: docs/03_langgraph_checkpoint/03_인메모리_체크포인터.md

"""인메모리 체크포인터 모듈."""

from __future__ import annotations

from typing import Any


class InMemoryCheckpointer:
    """인메모리 체크포인터."""

    def __init__(self, keep_last: int | None = None) -> None:
        """체크포인터를 초기화한다.

        Args:
            keep_last: thread_id별로 유지할 최신 체크포인트 개수. None이면 제한 없음.
        """
        self._store: dict[str, dict[str, dict[str, Any]]] = {}
        self._version: dict[str, int] = {}
        self._keep_last = keep_last

    def save(self, thread_id: str, state: dict[str, Any], metadata: dict[str, Any]) -> str:
        """상태 스냅샷을 저장한다.

        구현 내용:
            - thread_id별 버전을 증가시키고 checkpoint_id를 생성한다.
            - state/metadata를 저장하고 checkpoint_id를 반환한다.
            - keep_last 정책으로 오래된 스냅샷을 정리한다.
        """
        version = self._version.get(thread_id, 0) + 1
        self._version[thread_id] = version
        checkpoint_id = f"ckpt-{version:04d}"
        bucket = self._store.setdefault(thread_id, {})
        bucket[checkpoint_id] = {
            "state": state,
            "metadata": metadata,
        }
        self._trim_old(thread_id)
        return checkpoint_id

    def load(self, thread_id: str, checkpoint_id: str) -> dict[str, Any] | None:
        """특정 checkpoint_id의 스냅샷을 복구한다.

        구현 내용:
            - thread_id와 checkpoint_id로 저장된 스냅샷을 조회한다.
            - 없으면 None을 반환한다.
        """
        if thread_id not in self._store:
            return None
        return self._store[thread_id].get(checkpoint_id)

    def load_latest(self, thread_id: str) -> dict[str, Any] | None:
        """가장 최신 스냅샷을 복구한다.

        구현 내용:
            - thread_id의 최신 checkpoint_id를 찾는다.
            - 최신 스냅샷이 없으면 None을 반환한다.
        """
        if thread_id not in self._store:
            return None
        latest_version = self._version.get(thread_id)
        if latest_version is None:
            return None
        checkpoint_id = f"ckpt-{latest_version:04d}"
        return self._store[thread_id].get(checkpoint_id)

    def _trim_old(self, thread_id: str) -> None:
        """keep_last 정책에 따라 오래된 스냅샷을 정리한다."""
        if self._keep_last is None:
            return
        if self._keep_last <= 0:
            self._store.pop(thread_id, None)
            self._version.pop(thread_id, None)
            return
        bucket = self._store.get(thread_id, {})
        if len(bucket) <= self._keep_last:
            return
        sorted_items = sorted(bucket.items(), key=lambda item: item[0])
        to_remove = len(bucket) - self._keep_last
        for checkpoint_id, _ in sorted_items[:to_remove]:
            bucket.pop(checkpoint_id, None)
