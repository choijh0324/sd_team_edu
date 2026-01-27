# 목적: 스트리밍 이벤트 스키마를 정의한다.
# 설명: 토큰/메타데이터/에러/종료 이벤트를 일관된 구조로 전달한다.
# 디자인 패턴: DTO
# 참조: secondsession/api/chat/router/chat_router.py

"""대화 스트리밍 이벤트 스키마 모듈."""

from pydantic import BaseModel, Field

from secondsession.api.chat.const import StreamEventType
from secondsession.core.chat.const import ErrorCode, SafeguardLabel


class ChatStreamEvent(BaseModel):
    """스트리밍 이벤트 스키마."""

    type: StreamEventType = Field(..., description="이벤트 타입")
    content: str | None = Field(default=None, description="이벤트 내용")
    node: str | None = Field(default=None, description="노드 이름")
    error_code: ErrorCode | None = Field(default=None, description="에러 코드")
    safeguard_label: SafeguardLabel | None = Field(default=None, description="안전 라벨")
    trace_id: str = Field(..., description="스트리밍 추적 식별자")
    seq: int = Field(..., description="이벤트 순서")


# TODO:
# - type별 필수/선택 필드를 명확히 문서화한다.
# - error_code/safeguard_label을 metadata로 감싸는 규칙이 필요한지 검토한다.
