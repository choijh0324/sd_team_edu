# 목적: 주택 가격 통계 Tool을 정의한다.
# 설명: 필터 조건에 맞는 가격 통계를 계산한다.
# 디자인 패턴: 커맨드 패턴
# 참조: fourthsession/core/repository/sqlite/housing_repository.py

"""주택 가격 통계 Tool 모듈."""

from __future__ import annotations

from fourthsession.core.common.tools.base_tool import BaseTool
from fourthsession.core.repository.sqlite.housing_repository import HousingRepository


class HousingPriceStatsTool(BaseTool):
    """주택 가격 통계 Tool."""

    def __init__(self, repository: HousingRepository | None = None) -> None:
        """도구 의존성을 초기화한다.

        Args:
            repository (HousingRepository | None): 주택 레포지토리.
        """
        self._repository = repository or HousingRepository()

    @property
    def name(self) -> str:
        """Tool 이름을 반환한다."""
        return "housing_price_stats_tool"

    @property
    def description(self) -> str:
        """Tool 설명을 반환한다."""
        return "조건에 맞는 주택 가격 통계를 계산합니다."

    @property
    def input_schema(self) -> dict:
        """입력 스키마를 반환한다."""
        return {
            "type": "object",
            "properties": {
                "min_price": {"type": "number"},
                "max_price": {"type": "number"},
                "min_area": {"type": "number"},
                "max_area": {"type": "number"},
                "bedrooms": {"type": "integer"},
            },
            "required": [],
            "additionalProperties": False,
        }

    @property
    def example_request(self) -> dict:
        """예시 요청을 반환한다."""
        return {
            "min_area": 700,
            "max_area": 1500,
            "bedrooms": 3,
        }

    @property
    def example_response(self) -> dict:
        """예시 응답을 반환한다."""
        return {
            "count": 120,
            "average": 3400000.0,
            "median": 3200000.0,
            "min": 1200000.0,
            "max": 9100000.0,
        }

    @property
    def hints(self) -> dict:
        """도구 힌트를 반환한다."""
        return {
            "min_price": "최소 가격(이상) 필터",
            "max_price": "최대 가격(이하) 필터",
            "min_area": "최소 면적(이상) 필터",
            "max_area": "최대 면적(이하) 필터",
            "bedrooms": "침실 수 정확히 일치",
        }

    def execute(self, payload: dict) -> dict:
        """Tool을 실행한다.

        Args:
            payload (dict): 입력 데이터.

        Returns:
            dict: 실행 결과.
        """
        filters = dict(payload or {})
        return self._repository.get_price_stats(filters)
