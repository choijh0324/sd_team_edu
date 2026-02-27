# 목적: 관찰/피드백 루프 노드를 정의한다.
# 설명: 응답 품질을 검증하고 재계획 여부를 결정한다.
# 디자인 패턴: 상태 머신 패턴
# 참조: fourthsession/core/housing_agent/state

"""관찰/피드백 노드 모듈."""

from __future__ import annotations

from fourthsession.core.housing_agent.state.agent_state import HousingAgentState


class FeedbackLoopNode:
    """관찰/피드백 루프 노드."""

    def __call__(self, state: HousingAgentState) -> dict:
        """품질 검증 결과를 상태 업데이트로 반환한다.

        Args:
            state (HousingAgentState): 현재 상태.

        Returns:
            dict: 상태 업데이트 딕셔너리.
        """
        errors = list(state.errors or [])
        answer = state.answer
        tool_results = list(state.tool_results or [])

        has_meaningful_answer = isinstance(answer, str) and bool(answer.strip())
        can_retry = state.retry_count < state.max_retries

        if not has_meaningful_answer:
            errors.append("피드백 단계: 답변 품질 미달로 재계획이 필요합니다.")
            if can_retry:
                return {
                    "errors": errors,
                    "finalized": False,
                    "retry_count": state.retry_count + 1,
                }

            if tool_results:
                answer = "도구 실행은 완료되었지만 최종 답변 생성에 실패했습니다."
            elif errors:
                answer = "요청 처리 중 오류가 누적되어 답변을 생성하지 못했습니다."
            else:
                answer = "요청을 처리했지만 반환할 결과가 없습니다."

        if errors and not tool_results and can_retry:
            errors.append("피드백 단계: 실행 결과 부족으로 재계획을 시도합니다.")
            return {
                "errors": errors,
                "finalized": False,
                "retry_count": state.retry_count + 1,
            }

        return {
            "answer": answer,
            "errors": errors,
            "finalized": True,
        }
