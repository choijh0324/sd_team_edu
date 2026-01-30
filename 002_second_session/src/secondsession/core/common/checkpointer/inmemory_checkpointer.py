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
        # 동시성 주의:
        # - 멀티 스레드 환경에서는 _store/_version 접근이 경합될 수 있습니다.
        # - 실제 운영에서는 락(예: threading.Lock)으로 save/load를 감싸는 정책이 필요합니다.
        self._store: dict[str, dict[str, dict[str, Any]]] = {}
        self._version: dict[str, int] = {}
        self._keep_last = keep_last

    def save(self, thread_id: str, state: dict[str, Any], metadata: dict[str, Any]) -> str:
        """상태 스냅샷을 저장한다.

        TODO:
            - thread_id별 버전을 증가시키고 checkpoint_id를 생성한다.
            - state/metadata를 저장하고 checkpoint_id를 반환한다.
            - keep_last 정책으로 오래된 스냅샷을 정리한다.
        """
        version = self._version.get(thread_id, 0) + 1
        self._version[thread_id] = version
        checkpoint_id = f"{thread_id}:{version}"

        if thread_id not in self._store:
            self._store[thread_id] = {}
        self._store[thread_id][checkpoint_id] = {
            "state": dict(state),
            "metadata": dict(metadata),
        }
        self._cleanup(thread_id)
        return checkpoint_id

    def load(self, thread_id: str, checkpoint_id: str) -> dict[str, Any] | None:
        """특정 checkpoint_id의 스냅샷을 복구한다.

        TODO:
            - thread_id와 checkpoint_id로 저장된 스냅샷을 조회한다.
            - 없으면 None을 반환한다.
        """
        snapshot = self._store.get(thread_id, {}).get(checkpoint_id)
        if snapshot is None:
            return None
        return {
            "checkpoint_id": checkpoint_id,
            "state": dict(snapshot["state"]),
            "metadata": dict(snapshot["metadata"]),
        }

    def load_latest(self, thread_id: str) -> dict[str, Any] | None:
        """가장 최신 스냅샷을 복구한다.

        TODO:
            - thread_id의 최신 checkpoint_id를 찾는다.
            - 최신 스냅샷이 없으면 None을 반환한다.
        """
        latest_version = self._version.get(thread_id)
        if not latest_version:
            return None
        checkpoint_id = f"{thread_id}:{latest_version}"
        return self.load(thread_id, checkpoint_id)

    def _cleanup(self, thread_id: str) -> None:
        """keep_last 정책으로 오래된 스냅샷을 정리한다."""
        if self._keep_last is None:
            return
        if self._keep_last <= 0:
            self._store[thread_id] = {}
            return
        latest_version = self._version.get(thread_id, 0)
        min_version = max(1, latest_version - self._keep_last + 1)
        to_remove = []
        for checkpoint_id in self._store.get(thread_id, {}):
            try:
                version = int(checkpoint_id.split(":")[-1])
            except ValueError:
                continue
            if version < min_version:
                to_remove.append(checkpoint_id)
        for checkpoint_id in to_remove:
            self._store[thread_id].pop(checkpoint_id, None)
