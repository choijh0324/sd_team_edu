# 목적: 주택 에이전트 MCP 서버를 정의한다.
# 설명: MCP 서버 생성과 실행 책임을 캡슐화한다.
# 디자인 패턴: 팩토리 메서드 패턴
# 참조: fourthsession/mcp/tool_registry.py

"""주택 에이전트 MCP 서버 모듈."""

from __future__ import annotations

import logging
import os
from typing import Callable

from mcp.server.fastmcp import FastMCP

from fourthsession.core.common.logging_config import configure_logging
from fourthsession.mcp.tool_registry import HousingToolRegistry


LOGGER = logging.getLogger(__name__)


class HousingMcpServer:
    """주택 에이전트 MCP 서버."""

    def __init__(self, registry: HousingToolRegistry | None = None) -> None:
        """MCP 서버 구성 객체를 초기화한다.

        Args:
            registry (HousingToolRegistry | None): 도구 레지스트리.
        """
        self._registry = registry or HousingToolRegistry()
        self._server_name = "HousingAgentMCP"
        self._built_server: FastMCP | None = None

    def build(self) -> FastMCP:
        """MCP 서버 인스턴스를 구성한다.

        Returns:
            FastMCP: MCP 서버 인스턴스.
        """
        if self._built_server is not None:
            return self._built_server

        self._registry.register_tools()
        mcp = FastMCP(self._server_name)

        for card in self._registry.list_tool_cards():
            tool_name = card.get("name")
            if not isinstance(tool_name, str) or not tool_name.strip():
                continue
            handler = self._build_tool_handler(tool_name)
            mcp.tool()(handler)

        self._built_server = mcp
        return mcp

    def run(self) -> None:
        """MCP 서버를 실행한다."""
        configure_logging(service_name="fourthsession-mcp")
        mcp = self.build()
        transport = os.getenv("MCP_TRANSPORT", "stdio")
        mcp.run(transport=transport)

    def _build_tool_handler(self, tool_name: str) -> Callable[[dict], dict]:
        """도구 이름에 대응되는 MCP 핸들러를 생성한다."""
        tool = self._registry.get_tool(tool_name)

        def _handler(payload: dict) -> dict:
            LOGGER.info(
                "[mcp][tool_call][start] tool=%s payload_keys=%s",
                tool_name,
                sorted(payload.keys()) if isinstance(payload, dict) else [],
            )
            if tool is None:
                LOGGER.warning("[mcp][tool_call][missing] tool=%s", tool_name)
                return {"error": f"등록되지 않은 도구입니다: {tool_name}"}
            try:
                result = tool.execute(payload)
                LOGGER.info(
                    "[mcp][tool_call][end] tool=%s result_keys=%s",
                    tool_name,
                    sorted(result.keys()) if isinstance(result, dict) else [],
                )
                return result
            except Exception:
                LOGGER.exception("[mcp][tool_call][error] tool=%s", tool_name)
                raise

        _handler.__name__ = tool_name
        _handler.__doc__ = (
            tool.description if tool is not None else f"{tool_name} 도구를 실행합니다."
        )
        return _handler


if __name__ == "__main__":
    HousingMcpServer().run()
