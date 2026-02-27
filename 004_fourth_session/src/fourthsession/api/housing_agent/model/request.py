# 목적: 주택 에이전트 요청 모델을 정의한다.
# 설명: API 입력 스키마를 고정해 일관된 요청을 보장한다.
# 디자인 패턴: 데이터 전송 객체(DTO)
# 참조: fourthsession/api/housing_agent/service

"""주택 에이전트 요청 모델 모듈."""

from pydantic import BaseModel, Field


class HousingAgentRequest(BaseModel):
    """주택 에이전트 요청 모델."""

    question: str = Field(description="사용자 질문")
    trace_id: str | None = Field(default=None, description="추적 식별자")
    user_id: str | None = Field(default=None, description="사용자 식별자")
    preferred_tools: list[str] | None = Field(default=None, description="우선 사용 도구 목록")
    max_steps: int | None = Field(default=None, description="최대 실행 단계 수")

    @classmethod
    def from_payload(cls, payload: dict) -> "HousingAgentRequest":
        """딕셔너리 입력으로부터 요청 모델을 생성한다.

        Args:
            payload (dict): 원본 입력.

        Returns:
            HousingAgentRequest: 요청 모델.
        """
        if not isinstance(payload, dict):
            raise TypeError("payload는 dict 타입이어야 합니다.")

        question = payload.get("question")
        if not isinstance(question, str) or not question.strip():
            raise ValueError("question은 비어있지 않은 문자열이어야 합니다.")

        trace_id = payload.get("trace_id")
        if trace_id is not None:
            trace_id = str(trace_id).strip() or None

        user_id = payload.get("user_id")
        if user_id is not None:
            user_id = str(user_id).strip() or None

        preferred_tools_raw = payload.get("preferred_tools")
        preferred_tools: list[str] | None = None
        if preferred_tools_raw is not None:
            if not isinstance(preferred_tools_raw, list):
                raise ValueError("preferred_tools는 문자열 리스트여야 합니다.")

            normalized_tools = []
            for tool_name in preferred_tools_raw:
                if not isinstance(tool_name, str):
                    raise ValueError("preferred_tools의 각 항목은 문자열이어야 합니다.")
                stripped_tool_name = tool_name.strip()
                if stripped_tool_name:
                    normalized_tools.append(stripped_tool_name)
            preferred_tools = normalized_tools or None

        max_steps_raw = payload.get("max_steps")
        max_steps: int | None = None
        if max_steps_raw is not None:
            try:
                max_steps = int(max_steps_raw)
            except (TypeError, ValueError) as exc:
                raise ValueError("max_steps는 정수여야 합니다.") from exc
            if max_steps <= 0:
                raise ValueError("max_steps는 1 이상의 정수여야 합니다.")

        return cls(
            question=question.strip(),
            trace_id=trace_id,
            user_id=user_id,
            preferred_tools=preferred_tools,
            max_steps=max_steps,
        )
