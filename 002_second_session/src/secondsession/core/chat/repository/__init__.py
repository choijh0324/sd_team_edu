# 목적: 대화 저장소 패키지를 외부에 노출한다.
# 설명: Redis 기반 대화 내역 저장소를 집계한다.
# 디자인 패턴: 파사드
# 참조: secondsession/core/chat/repository/chat_history_repository.py

"""대화 저장소 패키지."""

from secondsession.core.chat.repository.chat_history_repository import ChatHistoryRepository

__all__ = ["ChatHistoryRepository"]
