# 목적: 스트리밍 이벤트 타입을 정의한다.
# 설명: SSE 전송 시 일관된 타입 값을 사용한다.
# 디자인 패턴: Value Object
# 참조: secondsession/api/chat/model/chat_stream_event.py

"""스트리밍 이벤트 타입 상수 모듈."""

from enum import Enum


class StreamEventType(Enum):
    """스트리밍 이벤트 타입."""

    TOKEN = "token"
    METADATA = "metadata"
    ERROR = "error"
    DONE = "done"


# 규약 요약:
# - token: content 필수
# - metadata: metadata 필수(content 사용하지 않음)
# - error: content + error_code 필수
# - done: content는 null
