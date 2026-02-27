# 목적: MCP Tool 레지스트리를 정의한다.
# 설명: 등록된 Tool 정보를 관리하고 도구 카드를 제공한다.
# 디자인 패턴: 레지스트리 패턴
# 참조: fourthsession/core/common/tools/base_tool.py

"""MCP Tool 레지스트리 모듈."""

from __future__ import annotations

from fourthsession.core.common.tools.base_tool import BaseTool
from fourthsession.core.housing_agent.tools.housing_list_tool import HousingListTool
from fourthsession.core.housing_agent.tools.housing_price_stats_tool import (
    HousingPriceStatsTool,
)


class HousingToolRegistry:
    """주택 에이전트 Tool 레지스트리."""

    def __init__(self) -> None:
        """레지스트리 내부 저장소를 초기화한다."""
        self._tools: dict[str, BaseTool] = {}

    def register_tools(self) -> None:
        """Tool 목록을 등록한다."""
        tools: list[BaseTool] = [
            HousingListTool(),
            HousingPriceStatsTool(),
        ]
        for tool in tools:
            self._tools[tool.name] = tool

    def list_tool_cards(self) -> list[dict]:
        """도구 카드 목록을 반환한다.

        Returns:
            list[dict]: 도구 카드 목록.
        """
        cards: list[dict] = []
        for tool in self._tools.values():
            card = {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            if hasattr(tool, "hints"):
                card["hints"] = getattr(tool, "hints")
            if hasattr(tool, "example_request"):
                card["example_request"] = getattr(tool, "example_request")
            if hasattr(tool, "example_response"):
                card["example_response"] = getattr(tool, "example_response")
            cards.append(card)
        return cards

    def get_tool(self, name: str):
        """이름으로 Tool을 조회한다."""
        return self._tools.get(name)
