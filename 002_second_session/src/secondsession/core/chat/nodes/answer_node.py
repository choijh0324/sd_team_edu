# 목적: 사용자 입력에 대한 답변을 생성한다.
# 설명: LLM 호출을 통해 응답을 만든다.
# 디자인 패턴: 전략 패턴 + 파이프라인 노드
# 참조: secondsession/core/chat/graphs/chat_graph.py

"""대화 응답 생성 노드 모듈."""

import logging

from langchain_openai import ChatOpenAI

from secondsession.core.chat.const import ErrorCode
from secondsession.core.chat.prompts.answer_prompt import ANSWER_PROMPT
from secondsession.core.chat.state.chat_state import ChatState
from secondsession.core.common.app_config import AppConfig
from secondsession.core.common.llm_client import LlmClient


class AnswerNode:
    """사용자 입력에 대한 답변을 생성하는 노드."""

    def __init__(self, llm_client: LlmClient | None = None) -> None:
        """노드 의존성을 초기화한다.

        Args:
            llm_client: LLM 클라이언트(선택).
        """
        self._llm_client = llm_client

    def run(self, state: ChatState) -> ChatState:
        """사용자 입력에 대한 답변을 생성한다.

        Args:
            state: 현재 대화 상태.

        Returns:
            ChatState: 답변 결과가 반영된 상태.
        """
        logger = logging.getLogger(__name__)
        user_message = state.get("last_user_message", "")
        logger.info("answer 시작")
        llm = self._get_llm()
        prompt = ANSWER_PROMPT.format(user_message=user_message)
        try:
            result = llm.invoke(prompt)
        except TimeoutError:
            return {"error_code": ErrorCode.TIMEOUT}
        except Exception:
            return {"error_code": ErrorCode.MODEL}

        content = str(getattr(result, "content", result)).strip()
        if not content:
            return {"error_code": ErrorCode.VALIDATION}
        logger.info("answer 완료 length=%s", len(content))
        return {"last_assistant_message": content}

    def _get_llm(self) -> ChatOpenAI:
        """LLM 인스턴스를 반환한다."""
        if self._llm_client is None:
            config = AppConfig.from_env()
            self._llm_client = LlmClient(config)
        return self._llm_client.chat_model()
