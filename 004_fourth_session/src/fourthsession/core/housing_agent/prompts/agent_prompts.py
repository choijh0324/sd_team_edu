# 목적: 주택 에이전트 프롬프트 템플릿을 정의한다.
# 설명: 계획/도구 선택/응답 생성에 필요한 프롬프트를 관리한다.
# 디자인 패턴: 템플릿 메서드 패턴
# 참조: fourthsession/core/housing_agent/graph

"""주택 에이전트 프롬프트 모듈."""

from fourthsession.core.housing_agent.const.agent_constants import HousingAgentConstants


class HousingAgentPrompts:
    """주택 에이전트 프롬프트 모음."""

    def plan_prompt(self) -> str:
        """계획 생성 프롬프트를 반환한다.

        Returns:
            str: 계획 생성용 프롬프트.
        """
        constants = HousingAgentConstants()
        return (
            "당신은 주택 데이터 질의를 처리하는 계획 수립 에이전트입니다.\n"
            "반드시 JSON 객체만 출력하세요. 마크다운, 설명 문장, 코드블록은 금지합니다.\n"
            "출력 스키마는 아래와 같습니다.\n"
            "{\n"
            '  "version": "'
            + constants.plan_version
            + '",\n'
            '  "goal": "<사용자 의도 요약>",\n'
            '  "steps": [\n'
            "    {\n"
            '      "id": "step-1",\n'
            '      "action": "'
            + constants.plan_action_name
            + '",\n'
            '      "tool": "<등록된 도구 이름>",\n'
            '      "input": {<도구 입력 파라미터>}\n'
            "    }\n"
            "  ]\n"
            "}\n"
            "규칙:\n"
            "1) steps는 최소 1개, 최대 3개로 구성합니다.\n"
            "2) tool은 반드시 제공된 도구 카드 중 하나만 사용합니다.\n"
            "3) input에는 도구 스키마에 없는 필드를 추가하지 않습니다.\n"
            "4) 동일 목적의 중복 step은 만들지 않습니다.\n"
            "5) 사용자 요청과 무관한 추측성 단계는 금지합니다.\n"
        )

    def tool_selection_prompt(self) -> str:
        """도구 선택 프롬프트를 반환한다.

        Returns:
            str: 도구 선택용 프롬프트.
        """
        return (
            "당신은 도구 선택기입니다.\n"
            "질문과 도구 카드 목록을 보고 가장 적절한 도구를 선택하세요.\n"
            "선택 규칙:\n"
            "1) 통계(평균, 중앙값, 최소/최대, 건수) 요청은 통계 도구를 우선 선택합니다.\n"
            "2) 개별 레코드 목록/샘플 조회 요청은 목록 도구를 우선 선택합니다.\n"
            "3) 조건이 복합적이면 필터를 정확히 구성하고 불필요한 도구 호출을 줄입니다.\n"
            "4) 질문에 필요한 정보가 도구로 해결되지 않으면 부족한 입력을 명시합니다.\n"
            "출력은 반드시 JSON 객체만 허용합니다.\n"
            '예시: {"selected_tool":"housing_price_stats_tool","reason":"가격 통계 요청","confidence":0.92}\n'
        )

    def answer_prompt(self) -> str:
        """응답 생성 프롬프트를 반환한다.

        Returns:
            str: 답변 생성용 프롬프트.
        """
        return (
            "당신은 주택 데이터 분석 결과를 사용자에게 설명하는 어시스턴트입니다.\n"
            "규칙:\n"
            "1) 답변은 한국어로 작성합니다.\n"
            "2) 도구 실행 결과에 근거해서만 답변합니다.\n"
            "3) 값이 없는 경우 추측하지 말고 '데이터 없음'을 명시합니다.\n"
            "4) 핵심 수치(건수/평균/중앙값/최소/최대)는 가능한 한 명확히 표시합니다.\n"
            "5) 불필요한 장문 설명보다 요약 중심으로 전달합니다.\n"
            "6) 오류가 있으면 오류 원인과 다음 조치(재시도 또는 조건 완화)를 짧게 안내합니다.\n"
        )
