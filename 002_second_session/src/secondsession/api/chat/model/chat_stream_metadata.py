# 목적: 메타데이터 스트리밍 페이로드 스키마를 정의한다.
# 설명: 메타데이터 이벤트의 JSON 구조를 고정한다.
# 디자인 패턴: DTO
# 참조: docs/02_backend_service_layer/03_메타데이터_스트리밍.md

"""메타데이터 스트리밍 페이로드 스키마 모듈."""

from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator

from secondsession.api.chat.const import MetadataEventType
from secondsession.core.chat.const import ErrorCode, SafeguardLabel


class ChatStreamMetadata(BaseModel):
    """메타데이터 스트리밍 페이로드."""

    event: MetadataEventType = Field(..., description="메타데이터 이벤트 이름(node_start 등)")
    message: str = Field(..., description="사용자/운영자에게 전달할 메시지")
    timestamp: str | None = Field(default=None, description="이벤트 생성 시각(ISO8601)")
    node: str | None = Field(default=None, description="관련 노드 이름")
    route: str | None = Field(default=None, description="라우팅 결과")
    error_code: ErrorCode | None = Field(default=None, description="에러 코드")
    safeguard_label: SafeguardLabel | None = Field(default=None, description="안전 라벨")

    @field_validator("timestamp", mode="before")
    @classmethod
    def fill_timestamp(cls, value: str | None) -> str:
        """timestamp 기본 값을 생성한다."""
        if value:
            return value
        return datetime.now(timezone.utc).isoformat()


# 규약:
# - event, message는 필수다.
# - timestamp는 ISO8601 문자열을 사용한다.
