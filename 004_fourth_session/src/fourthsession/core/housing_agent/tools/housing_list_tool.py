# 목적: 주택 목록 조회 Tool을 정의한다.
# 설명: 필터 조건에 맞는 주택 목록을 반환한다.
# 디자인 패턴: 커맨드 패턴
# 참조: fourthsession/core/repository/sqlite/housing_repository.py

"""주택 목록 조회 Tool 모듈."""

from __future__ import annotations

from fourthsession.core.housing_agent.const.agent_constants import HousingAgentConstants
from fourthsession.core.common.tools.base_tool import BaseTool
from fourthsession.core.repository.sqlite.housing_repository import HousingRepository


class HousingListTool(BaseTool):
    """주택 목록 조회 Tool."""

    def __init__(self, repository: HousingRepository | None = None) -> None:
        """도구 의존성을 초기화한다.

        Args:
            repository (HousingRepository | None): 주택 레포지토리.
        """
        self._repository = repository or HousingRepository()
        self._constants = HousingAgentConstants()

    @property
    def name(self) -> str:
        """Tool 이름을 반환한다."""
        return "housing_list_tool"

    @property
    def description(self) -> str:
        """Tool 설명을 반환한다."""
        return "조건에 맞는 주택 목록을 조회합니다."

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
                "limit": {"type": "integer", "minimum": 1},
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
            "limit": 5,
        }

    @property
    def example_response(self) -> dict:
        """예시 응답을 반환한다."""
        return {
            "count": 2,
            "items": [
                {"price": 3200000.0, "area": 980.0, "bedrooms": 3},
                {"price": 3500000.0, "area": 1120.0, "bedrooms": 3},
            ],
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
            "limit": f"반환 개수 제한(기본 {self._constants.default_list_limit})",
        }

    def execute(self, payload: dict) -> dict:
        """Tool을 실행한다.

        Args:
            payload (dict): 입력 데이터.

        Returns:
            dict: 실행 결과.
        """
        filters = dict(payload or {})
        limit = filters.get("limit")
        if limit is None:
            filters["limit"] = self._constants.default_list_limit
        else:
            filters["limit"] = max(1, int(limit))

        houses = self._repository.list_houses(filters)
        return {"count": len(houses), "items": houses}
