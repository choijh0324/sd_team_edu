# 목적: 대화 내역 항목 스키마를 정의한다.
# 설명: history에 저장되는 항목을 검증하기 위한 모델이다.
# 디자인 패턴: DTO
# 참조: secondsession/core/chat/state/chat_state.py

"""대화 내역 항목 스키마 모듈."""

from typing import Literal

from pydantic import BaseModel, Field


class ChatHistoryItem(BaseModel):
    """대화 내역 항목."""

    role: Literal["user", "assistant", "system", "tool"] = Field(
        ..., description="역할(user/assistant/system/tool)"
    )
    content: str = Field(..., min_length=1, max_length=4000, description="메시지 내용")
    created_at: str | None = Field(default=None, description="생성 시각(ISO8601)")
    metadata: dict | None = Field(default=None, description="메타데이터")
    message_id: str | None = Field(default=None, description="메시지 식별자")


# TODO:
# - content 길이 정책을 서비스 정책에 맞게 조정한다.
