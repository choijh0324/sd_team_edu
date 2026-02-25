# 목적: 서비스 전역 에러 코드를 정의한다.
# 설명: 에러 코드/사용자 메시지를 함께 관리해 일관성을 유지한다.
# 디자인 패턴: Value Object
# 참조: nextStep.md, thirdsession/core/rag/state/chat_state.py

"""에러 코드 상수 모듈."""

from __future__ import annotations

from enum import Enum
from typing import Any


class ErrorCode(Enum):
    """에러 코드와 사용자 메시지 정의."""

    # 공통
    VALIDATION = ("validation_error", "출력 형식 오류로 간단 요약을 제공합니다.")
    TIMEOUT = ("timeout", "처리가 지연되었습니다. 잠시 후 다시 시도해 주세요.")

    # 검색/후처리 도메인
    RETRIEVAL_EMPTY = ("retrieval_empty", "관련 정보를 찾지 못했습니다. 일반 설명을 제공합니다.")
    RETRIEVAL_FAILED = ("retrieval_failed", "검색 처리 중 문제가 발생했습니다. 다시 시도해 주세요.")
    POSTPROCESS_FAILED = ("postprocess_failed", "후처리 중 문제가 발생해 기본 응답을 제공합니다.")

    # 생성/모델 도메인
    LLM_FAILED = ("llm_failed", "답변 생성 중 문제가 발생해 기본 응답을 제공합니다.")
    MODEL_OUTPUT_INVALID = ("model_output_invalid", "모델 출력 형식이 올바르지 않아 기본 응답을 제공합니다.")

    # 인프라/외부 연동 도메인
    TOOL = ("tool_error", "외부 도구 호출에 실패했습니다. 기본 안내만 제공합니다.")
    QUEUE_FAILED = ("queue_failed", "작업 큐 처리 중 오류가 발생했습니다.")
    STREAM_FAILED = ("stream_failed", "스트리밍 처리 중 오류가 발생했습니다.")
    REDIS_FAILED = ("redis_failed", "저장소 연결에 문제가 발생했습니다.")

    # 정책/보안 도메인
    SAFEGUARD = ("safeguard_blocked", "요청을 처리할 수 없습니다. 다른 질문을 해주세요.")
    PROMPT_INJECTION = ("prompt_injection_blocked", "안전하지 않은 요청으로 판단되어 차단되었습니다.")
    PII = ("pii_blocked", "개인정보 보호 정책에 따라 요청을 처리할 수 없습니다.")
    HARMFUL = ("harmful_blocked", "유해 요청으로 분류되어 처리할 수 없습니다.")

    # 기본/미분류
    UNKNOWN = ("unknown_error", "처리 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.")

    @property
    def code(self) -> str:
        """시스템 식별자 문자열을 반환한다."""
        return self.value[0]

    @property
    def user_message(self) -> str:
        """사용자에게 노출할 메시지를 반환한다."""
        return self.value[1]

    @property
    def domain(self) -> str:
        """에러 코드의 도메인 그룹을 반환한다."""
        if self in {ErrorCode.RETRIEVAL_EMPTY, ErrorCode.RETRIEVAL_FAILED, ErrorCode.POSTPROCESS_FAILED}:
            return "retrieval"
        if self in {ErrorCode.LLM_FAILED, ErrorCode.MODEL_OUTPUT_INVALID}:
            return "generation"
        if self in {ErrorCode.QUEUE_FAILED, ErrorCode.STREAM_FAILED, ErrorCode.REDIS_FAILED, ErrorCode.TOOL}:
            return "infrastructure"
        if self in {ErrorCode.SAFEGUARD, ErrorCode.PROMPT_INJECTION, ErrorCode.PII, ErrorCode.HARMFUL}:
            return "safeguard"
        return "common"

    @property
    def retriable(self) -> bool:
        """재시도 권장 여부를 반환한다."""
        return self in {
            ErrorCode.TIMEOUT,
            ErrorCode.RETRIEVAL_FAILED,
            ErrorCode.LLM_FAILED,
            ErrorCode.QUEUE_FAILED,
            ErrorCode.STREAM_FAILED,
            ErrorCode.REDIS_FAILED,
            ErrorCode.TOOL,
            ErrorCode.UNKNOWN,
        }

    @classmethod
    def from_code(cls, code: str | None) -> "ErrorCode":
        """코드 문자열을 ErrorCode로 변환한다."""
        if code is None:
            return cls.UNKNOWN
        normalized = code.strip().lower()
        for item in cls:
            if item.code == normalized:
                return item
        return cls.UNKNOWN

    @classmethod
    def from_exception(cls, error: Exception) -> "ErrorCode":
        """예외 타입/메시지를 기반으로 공통 에러 코드를 매핑한다."""
        message = str(error).lower()
        if isinstance(error, TimeoutError) or "timeout" in message:
            return cls.TIMEOUT
        if isinstance(error, ValueError):
            return cls.VALIDATION
        if "redis" in message:
            return cls.REDIS_FAILED
        if "queue" in message:
            return cls.QUEUE_FAILED
        if "stream" in message:
            return cls.STREAM_FAILED
        if "retriev" in message or "search" in message:
            return cls.RETRIEVAL_FAILED
        if "llm" in message or "model" in message:
            return cls.LLM_FAILED
        return cls.UNKNOWN

    def to_api(self, trace_id: str | None = None, detail: str | None = None) -> dict[str, Any]:
        """API 응답/로그 공통 포맷으로 변환한다."""
        payload: dict[str, Any] = {
            "error_code": self.code,
            "domain": self.domain,
            "message": self.user_message,
            "retriable": self.retriable,
        }
        if trace_id is not None:
            payload["trace_id"] = trace_id
        if detail is not None and detail.strip() != "":
            payload["detail"] = detail
        return payload

    def to_log(self, trace_id: str | None = None, **extra: Any) -> dict[str, Any]:
        """로그 적재용 공통 포맷으로 변환한다."""
        payload: dict[str, Any] = {
            "error_code": self.code,
            "domain": self.domain,
            "retriable": self.retriable,
        }
        if trace_id is not None:
            payload["trace_id"] = trace_id
        payload.update(extra)
        return payload

# 호환용 별칭: 기존 외부 코드에서 사용하던 이름을 유지한다.
ErrorCode.MODEL = ErrorCode.LLM_FAILED
