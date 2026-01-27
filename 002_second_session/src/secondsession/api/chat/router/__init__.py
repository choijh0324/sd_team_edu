# 목적: 채팅 라우터를 외부에 노출한다.
# 설명: 대화 라우터를 집계한다.
# 디자인 패턴: 파사드
# 참조: secondsession/main.py

"""채팅 API 라우터 패키지."""

from secondsession.api.chat.router.chat_router import router as chat_router

__all__ = ["chat_router"]
