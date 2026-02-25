# 목적: 잡 스트리밍 응답 스키마를 정의한다.
# 설명: 스트리밍 이벤트의 표준 형태를 고정한다.
# 디자인 패턴: DTO
# 참조: docs/04_rag_pipeline_design/03_생성_단계_설계.md

"""잡 스트리밍 응답 스키마 모듈."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class JobStreamEventType(str, Enum):
    """스트리밍 이벤트 타입."""

    TOKEN = "token"
    REFERENCES = "references"
    ERROR = "error"
    DONE = "DONE"


class JobStreamEventStatus(str, Enum):
    """스트리밍 이벤트 상태."""

    IN_PROGRESS = "in_progress"
    END = "end"


class JobStreamResponse(BaseModel):
    """잡 스트리밍 응답 스키마."""

    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=True,
    )

    type: JobStreamEventType = Field(..., description="이벤트 타입(token/references/error/DONE)")
    status: JobStreamEventStatus | None = Field(default=None, description="이벤트 상태(in_progress/end)")
    content: str | None = Field(default=None, description="토큰/메시지 내용")
    index: int | None = Field(default=None, description="토큰 순서(선택)")
    items: list[dict[str, Any]] | None = Field(default=None, description="근거 문서 목록(선택)")

    def todo_extend_fields(self) -> None:
        """스트리밍 필드가 이미 확정된 상태임을 나타내는 호환 메서드."""

    @model_validator(mode="after")
    def validate_by_event_type(self) -> "JobStreamResponse":
        """이벤트 타입별 필드 규칙을 검증한다."""
        if self.type == JobStreamEventType.TOKEN:
            if self.status is None:
                raise ValueError("token 이벤트는 status가 필요합니다.")
            if self.status not in {JobStreamEventStatus.IN_PROGRESS, JobStreamEventStatus.END}:
                raise ValueError("token 이벤트 status는 in_progress 또는 end만 허용됩니다.")
            if self.items is not None:
                raise ValueError("token 이벤트에서는 items를 사용할 수 없습니다.")
            if self.status == JobStreamEventStatus.IN_PROGRESS and self.content is None:
                raise ValueError("token(in_progress) 이벤트는 content가 필요합니다.")
            return self

        if self.type == JobStreamEventType.REFERENCES:
            if self.status != JobStreamEventStatus.END:
                raise ValueError("references 이벤트 status는 end여야 합니다.")
            if self.items is None:
                raise ValueError("references 이벤트는 items가 필요합니다.")
            if self.content is not None:
                raise ValueError("references 이벤트에서는 content를 사용할 수 없습니다.")
            if self.index is not None:
                raise ValueError("references 이벤트에서는 index를 사용할 수 없습니다.")
            return self

        if self.type == JobStreamEventType.ERROR:
            if self.content is None or self.content.strip() == "":
                raise ValueError("error 이벤트는 content가 필요합니다.")
            if self.items is not None:
                raise ValueError("error 이벤트에서는 items를 사용할 수 없습니다.")
            if self.index is not None:
                raise ValueError("error 이벤트에서는 index를 사용할 수 없습니다.")
            if self.status is not None and self.status != JobStreamEventStatus.END:
                raise ValueError("error 이벤트 status는 end만 허용됩니다.")
            return self

        if self.type == JobStreamEventType.DONE:
            if self.status is not None or self.content is not None or self.index is not None or self.items is not None:
                raise ValueError("DONE 이벤트는 type 외 필드를 가질 수 없습니다.")
            return self

        raise ValueError("지원하지 않는 이벤트 타입입니다.")
