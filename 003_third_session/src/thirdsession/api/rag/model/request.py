# 목적: rag 요청 모델을 정의한다.
# 설명: FastAPI 요청 바디 스키마를 명확히 하기 위한 DTO이다.
# 디자인 패턴: DTO
# 참조: thirdsession/api/rag/router/rag_router.py, thirdsession/api/rag/service/rag_service.py

"""rag 요청 모델 모듈."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RagRequest(BaseModel):
    """rag 요청 모델."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="사용자 질문",
    )
    user_id: str | None = Field(
        default=None,
        max_length=128,
        description="사용자 식별자(선택)",
    )
    thread_id: str | None = Field(
        default=None,
        max_length=128,
        description="대화 복구용 thread_id(선택)",
    )
    session_id: str | None = Field(
        default=None,
        max_length=128,
        description="세션 식별자(선택)",
    )
    trace_id: str | None = Field(
        default=None,
        max_length=128,
        description="요청 추적 ID(선택)",
    )
    history: list[dict[str, Any]] | None = Field(
        default=None,
        description="이전 대화 내역(선택)",
    )
    top_k: int | None = Field(
        default=None,
        ge=1,
        le=20,
        description="검색 문서 개수 제한(선택, 1~20)",
    )
    collection: str | None = Field(
        default=None,
        max_length=64,
        description="검색 컬렉션 이름(선택)",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="추가 메타데이터(선택)",
    )

    def todo_extend_fields(self) -> None:
        """요청 필드가 이미 확장된 상태임을 나타내는 호환 메서드."""

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        """질문 문자열이 비어 있지 않은지 검증한다."""
        if value.strip() == "":
            raise ValueError("question은 공백만 입력할 수 없습니다.")
        return value

    @field_validator("user_id", "thread_id", "session_id", "trace_id", "collection", mode="before")
    @classmethod
    def normalize_optional_string(cls, value: Any) -> Any:
        """선택 문자열 필드의 빈 문자열을 None으로 정규화한다."""
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        """메타데이터 형식과 직렬화 가능 여부를 검증한다."""
        if value is None:
            return None
        if len(value) > 50:
            raise ValueError("metadata 항목 수는 최대 50개까지 허용됩니다.")
        for key in value:
            if key.strip() == "":
                raise ValueError("metadata 키는 빈 문자열일 수 없습니다.")
            if len(key) > 64:
                raise ValueError("metadata 키 길이는 최대 64자입니다.")
        try:
            json.dumps(value, ensure_ascii=False)
        except TypeError as error:
            raise ValueError("metadata는 JSON 직렬화 가능한 값만 허용됩니다.") from error
        return value

    @model_validator(mode="after")
    def merge_top_level_into_metadata(self) -> "RagRequest":
        """상위 필드를 metadata로 병합해 서비스 계층 호환성을 유지한다."""
        merged_metadata = dict(self.metadata or {})
        if self.thread_id is not None:
            merged_metadata["thread_id"] = self.thread_id
        if self.session_id is not None:
            merged_metadata["session_id"] = self.session_id
        if self.trace_id is not None:
            merged_metadata["trace_id"] = self.trace_id
        if self.top_k is not None:
            merged_metadata["top_k"] = self.top_k
        if self.collection is not None:
            merged_metadata["collection"] = self.collection
        if self.history is not None:
            merged_metadata["history"] = self.history
        self.metadata = merged_metadata or None
        return self
