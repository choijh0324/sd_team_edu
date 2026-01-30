# 목적: 안전 분류 노드를 정의한다.
# 설명: 사용자 입력을 안전 라벨로 분류한다.
# 디자인 패턴: 전략 패턴 + 파이프라인 노드
# 참조: secondsession/core/chat/graphs/chat_graph.py

"""안전 분류 노드 모듈."""

from langchain_openai import ChatOpenAI

from secondsession.core.chat.const import ErrorCode, SafeguardLabel
from secondsession.core.chat.prompts.safeguard_prompt import SAFEGUARD_PROMPT
from secondsession.core.chat.state.chat_state import ChatState
from secondsession.core.common.app_config import AppConfig
from secondsession.core.common.llm_client import LlmClient


class SafeguardNode:
    """사용자 입력을 안전 라벨로 분류하는 노드."""

    def __init__(self, llm_client: LlmClient | None = None) -> None:
        """노드 의존성을 초기화한다.

        Args:
            llm_client: LLM 클라이언트(선택).
        """
        self._llm_client = llm_client

    def run(self, state: ChatState) -> ChatState:
        """사용자 입력을 안전 라벨로 분류한다.

        Args:
            state: 현재 대화 상태.

        Returns:
            ChatState: 안전 라벨이 반영된 상태.
        """
        user_message = state.get("last_user_message", "")
        llm = self._get_llm()
        prompt = SAFEGUARD_PROMPT.format(user_input=user_message)
        try:
            result = llm.invoke(prompt)
        except TimeoutError:
            return {
                "safeguard_label": SafeguardLabel.PROMPT_INJECTION,
                "error_code": ErrorCode.TIMEOUT,
            }
        except Exception:
            return {
                "safeguard_label": SafeguardLabel.PROMPT_INJECTION,
                "error_code": ErrorCode.MODEL,
            }

        label = self._parse_label(str(getattr(result, "content", result)))
        response: ChatState = {"safeguard_label": label}
        if label != SafeguardLabel.PASS:
            response["error_code"] = ErrorCode.SAFEGUARD
        return response

    def _get_llm(self) -> ChatOpenAI:
        """LLM 인스턴스를 반환한다."""
        if self._llm_client is None:
            config = AppConfig.from_env()
            self._llm_client = LlmClient(config)
        return self._llm_client.chat_model()

    def _parse_label(self, raw: str) -> SafeguardLabel:
        """라벨 문자열을 SafeguardLabel로 변환한다."""
        value = raw.strip().upper()
        if value == SafeguardLabel.PASS.value:
            return SafeguardLabel.PASS
        if value == SafeguardLabel.PII.value:
            return SafeguardLabel.PII
        if value == SafeguardLabel.HARMFUL.value:
            return SafeguardLabel.HARMFUL
        if value == SafeguardLabel.PROMPT_INJECTION.value:
            return SafeguardLabel.PROMPT_INJECTION
        return SafeguardLabel.PROMPT_INJECTION
