# 목적: rag 응답 모델을 정의한다.
# 설명: FastAPI 응답 스키마를 명확히 하기 위한 DTO이다.
# 디자인 패턴: DTO
# 참조: thirdsession/api/rag/router/rag_router.py, thirdsession/api/rag/service/rag_service.py

"""rag 응답 모델 모듈."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RagSummaryPayload(BaseModel):
    """요약 응답 섹션."""

    answer: str = Field(..., description="요약 답변")
    citations: list[str] = Field(default_factory=list, description="요약 기준 근거 source_id 목록")


class RagSourceItem(BaseModel):
    """근거 문서 항목."""

    source_id: str = Field(..., description="근거 식별자")
    title: str | None = Field(default=None, description="문서 제목(선택)")
    snippet: str | None = Field(default=None, description="문서 요약/본문 일부(선택)")
    score: float | None = Field(default=None, description="검색/재랭킹 점수(선택)")
    metadata: dict[str, Any] | None = Field(default=None, description="문서 메타데이터(선택)")


class RagDetailPayload(BaseModel):
    """상세 응답 섹션."""

    question: str | None = Field(default=None, description="원본 질문")
    answer: str = Field(..., description="상세 답변")
    sources: list[RagSourceItem] = Field(default_factory=list, description="상세 근거 목록")
    error_code: str | None = Field(default=None, description="오류 코드(선택)")
    safeguard_label: str | None = Field(default=None, description="안전 정책 라벨(선택)")


class RagMetaPayload(BaseModel):
    """메타 응답 섹션."""

    trace_id: str | None = Field(default=None, description="추적 ID")
    thread_id: str | None = Field(default=None, description="대화 복구용 thread_id")
    session_id: str | None = Field(default=None, description="세션 식별자")
    user_id: str | None = Field(default=None, description="사용자 식별자")
    route: str | None = Field(default=None, description="그래프 라우팅 결과(선택)")
    retrieval_stats: dict[str, Any] | None = Field(default=None, description="검색 통계(선택)")
    metadata: dict[str, Any] | None = Field(default=None, description="부가 메타데이터(선택)")


class RagResponse(BaseModel):
    """rag 응답 모델."""

    answer: str = Field(..., description="최종 답변")
    citations: list[str] = Field(default_factory=list, description="근거 source_id 목록")
    trace_id: str | None = Field(None, description="추적 ID(선택)")
    summary: RagSummaryPayload = Field(..., description="요약 응답 섹션")
    detail: RagDetailPayload = Field(..., description="상세 응답 섹션")
    meta: RagMetaPayload = Field(..., description="메타 응답 섹션")

    def todo_extend_fields(self) -> None:
        """응답 필드가 이미 확장된 상태임을 나타내는 호환 메서드."""
