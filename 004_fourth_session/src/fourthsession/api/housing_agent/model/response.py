# 목적: 주택 에이전트 응답 모델을 정의한다.
# 설명: API 응답 스키마를 고정해 반환 구조를 일관되게 한다.
# 디자인 패턴: 데이터 전송 객체(DTO)
# 참조: fourthsession/api/housing_agent/service

"""주택 에이전트 응답 모델 모듈."""

from pydantic import BaseModel, Field


class HousingAgentResponse(BaseModel):
    """주택 에이전트 응답 모델."""

    answer: str = Field(description="최종 답변")
    trace_id: str | None = Field(default=None, description="추적 식별자")
    metadata: dict | None = Field(default=None, description="추가 메타데이터")

    @classmethod
    def from_result(cls, result: dict) -> "HousingAgentResponse":
        """실행 결과에서 응답 모델을 생성한다.

        Args:
            result (dict): 에이전트 실행 결과.

        Returns:
            HousingAgentResponse: 응답 모델.
        """
        if not isinstance(result, dict):
            raise TypeError("result는 dict 타입이어야 합니다.")

        raw_answer = result.get("answer")
        answer: str
        if raw_answer is None:
            answer = "요청 처리 결과가 비어 있습니다."
        elif isinstance(raw_answer, str):
            answer = raw_answer.strip() or "요청 처리 결과가 비어 있습니다."
        else:
            answer = str(raw_answer).strip() or "요청 처리 결과가 비어 있습니다."

        trace_id = result.get("trace_id")
        if trace_id is not None:
            trace_id = str(trace_id).strip() or None

        raw_metadata = result.get("metadata")
        metadata: dict | None
        if isinstance(raw_metadata, dict):
            metadata = raw_metadata
        else:
            metadata = {
                "tool_results": result.get("tool_results", []),
                "errors": result.get("errors", []),
                "plan": result.get("plan"),
            }
            if not metadata["tool_results"] and not metadata["errors"] and metadata["plan"] is None:
                metadata = None

        return cls(answer=answer, trace_id=trace_id, metadata=metadata)
