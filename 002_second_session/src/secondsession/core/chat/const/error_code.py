# 목적: 서비스 전역 에러 코드를 정의한다.
# 설명: 에러 코드/사용자 메시지를 함께 관리해 일관성을 유지한다.
# 디자인 패턴: Value Object
# 참조: docs/01_langgraph_to_service/02_폴백_구현_패턴.md

"""에러 코드 상수 모듈."""

from enum import Enum


class ErrorCode(Enum):
    """에러 코드와 사용자 메시지 정의."""

    VALIDATION = ("validation_error", "출력 형식 오류로 간단 요약을 제공합니다.")
    TOOL = ("tool_error", "외부 도구 호출에 실패했습니다. 기본 안내만 제공합니다.")
    RETRIEVAL_EMPTY = ("retrieval_empty", "관련 정보를 찾지 못했습니다. 일반 설명을 제공합니다.")
    TIMEOUT = ("timeout", "처리가 지연되었습니다. 잠시 후 다시 시도해 주세요.")
    SAFEGUARD = ("safeguard_blocked", "요청을 처리할 수 없습니다. 다른 질문을 해주세요.")
    UNKNOWN = ("unknown_error", "처리 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.")
    HISTORY = ("history_error", "대화 기록 처리에 실패했습니다. 기본 응답을 제공합니다.")
    SUMMARY = ("summary_error", "요약 처리에 실패했습니다. 기본 응답을 제공합니다.")
    PARALLEL = ("parallel_error", "병렬 처리에 실패했습니다. 기본 응답을 제공합니다.")

    @property
    def code(self) -> str:
        """시스템 식별자 문자열을 반환한다."""
        return self.value[0]

    @property
    def user_message(self) -> str:
        """사용자에게 노출할 메시지를 반환한다."""
        return self.value[1]


# 공통 매핑 규칙(기본):
# - SAFEGUARD 라벨이 PASS가 아니면 SAFEGUARD 코드로 강제한다.
# - 응답이 비어 있으면 VALIDATION 코드로 전환한다.
# - 타임아웃/모델 오류는 TIMEOUT/MODEL로 기록한다.
