# 목적: 대화 내역 항목 스키마를 정의한다.
# 설명: history에 저장되는 항목을 검증하기 위한 모델이다.
# 디자인 패턴: DTO
# 참조: secondsession/core/chat/state/chat_state.py

"""대화 내역 항목 스키마 모듈."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ChatHistoryItem(BaseModel):
    """대화 내역 항목."""

    role: Literal["user", "assistant", "system"] = Field(
        ...,
        description="역할(user/assistant/system)",
    )
    content: str = Field(..., description="메시지 내용")
    created_at: str | None = Field(default=None, description="생성 시각(ISO8601)")

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        """콘텐츠 길이를 검증한다."""
        content = value.strip()
        if not content:
            raise ValueError("content는 비어 있을 수 없습니다.")
        if len(content) > 2000:
            raise ValueError("content는 2000자를 초과할 수 없습니다.")
        return content


# content 길이 정책은 서비스 정책에 맞게 조정할 수 있다.
