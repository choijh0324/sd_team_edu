# 목적: 대화 요약 노드를 정의한다.
# 설명: 대화 내역을 요약해 summary에 저장한다.
# 디자인 패턴: 전략 패턴 + 파이프라인 노드
# 참조: secondsession/core/chat/graphs/chat_graph.py

"""대화 요약 노드 모듈."""

import logging

from langchain_openai import ChatOpenAI

from secondsession.core.chat.const import ErrorCode
from secondsession.core.chat.prompts.summary_prompt import SUMMARY_PROMPT
from secondsession.core.chat.state.chat_state import ChatState
from secondsession.core.common.app_config import AppConfig
from secondsession.core.common.llm_client import LlmClient


class SummaryNode:
    """대화 요약을 생성하는 노드."""

    def __init__(self, llm_client: LlmClient | None = None) -> None:
        """노드 의존성을 초기화한다.

        Args:
            llm_client: LLM 클라이언트(선택).
        """
        self._llm_client = llm_client

    def run(self, state: ChatState) -> ChatState:
        """대화 요약을 생성한다.

        Args:
            state: 현재 대화 상태.

        Returns:
            ChatState: 요약 결과가 반영된 상태.
        """
        logger = logging.getLogger(__name__)
        chat_history = self._render_history(state.get("history", []))
        logger.info("summary 시작 items=%s", len(state.get("history", [])))
        llm = self._get_llm()
        prompt = SUMMARY_PROMPT.format(chat_history=chat_history)
        try:
            result = llm.invoke(prompt)
        except TimeoutError:
            return {"error_code": ErrorCode.TIMEOUT}
        except Exception:
            return {"error_code": ErrorCode.MODEL}

        summary = str(getattr(result, "content", result)).strip()
        if not summary:
            return {"error_code": ErrorCode.VALIDATION}
        logger.info("summary 완료 length=%s", len(summary))
        return {"summary": summary}

    def _get_llm(self) -> ChatOpenAI:
        """LLM 인스턴스를 반환한다."""
        if self._llm_client is None:
            config = AppConfig.from_env()
            self._llm_client = LlmClient(config)
        return self._llm_client.chat_model()

    def _render_history(self, history: list[dict]) -> str:
        """대화 내역을 요약용 문자열로 변환한다."""
        lines: list[str] = []
        for item in history:
            role = item.get("role", "unknown")
            content = item.get("content", "")
            lines.append(f"{role}: {content}")
        return "\n".join(lines)
