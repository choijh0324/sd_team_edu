# 목적: 주택 에이전트 전용 상수 묶음을 정의한다.
# 설명: 모델명, 기본 정책, 경로 같은 값을 한곳에 모은다.
# 디자인 패턴: 상수 객체 패턴
# 참조: fourthsession/core/housing_agent/*

"""주택 에이전트 상수 모듈."""


class HousingAgentConstants:
    """주택 에이전트에서 공통으로 사용하는 상수 묶음."""

    def __init__(self) -> None:
        """상수 값을 초기화한다."""
        self.default_max_retries = 2
        self.default_list_limit = 10
        self.plan_action_name = "query_housing_data"
        self.plan_version = "v1"
