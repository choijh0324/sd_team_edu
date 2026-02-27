# 목적: 주택 에이전트 API 상수를 정의한다.
# 설명: 라우팅 경로, 태그, 버전 같은 값을 정리한다.
# 디자인 패턴: 상수 객체 패턴
# 참조: fourthsession/api/housing_agent/router

"""주택 에이전트 API 상수 모듈."""


class HousingApiConstants:
    """주택 에이전트 API 상수."""

    def __init__(self) -> None:
        """상수 값을 초기화한다."""
        self.api_prefix = "/api/v1"
        self.agent_path = "/housing/agent"
        self.job_path = "/housing/jobs"
        self.job_cancel_path = "/housing/jobs/{job_id}/cancel"
        self.job_status_path = "/housing/jobs/{job_id}/status"
        self.job_stream_path = "/housing/jobs/{job_id}/stream"
        self.tag = "housing-agent"
        self.job_tag = "housing-job"
