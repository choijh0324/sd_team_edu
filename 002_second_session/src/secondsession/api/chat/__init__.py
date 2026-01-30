# 목적: 채팅 API 패키지 진입점을 제공한다.
# 설명: 라우터와 모델/서비스 모듈을 노출한다.
# 디자인 패턴: 파사드
# 참조: secondsession/main.py

"""채팅 API 패키지."""

from secondsession.api.chat.router import ChatRouter

__all__ = ["ChatRouter"]
