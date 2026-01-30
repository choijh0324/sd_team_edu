# 목적: 안전 분류 노드를 정의한다.
# 설명: 사용자 입력을 안전 라벨로 분류한다.
# 디자인 패턴: 커맨드
# 참조: secondsession/core/chat/graphs/chat_graph.py

"""안전 분류 노드 모듈."""

import logging
import os

import httpx

from secondsession.core.chat.const.error_code import ErrorCode
from secondsession.core.chat.const.safeguard_label import SafeguardLabel
from secondsession.core.chat.prompts.safeguard_prompt import SAFEGUARD_PROMPT
from secondsession.core.chat.state.chat_state import ChatState

_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
_DEFAULT_MODEL = "gpt-4o-mini"
_API_URL = "https://api.openai.com/v1/chat/completions"


def safeguard_node(state: ChatState) -> dict:
    """사용자 입력을 안전 라벨로 분류한다.

    TODO:
        - LLM 클라이언트를 연결한다.
        - SAFEGUARD_PROMPT.format으로 사용자 입력을 결합한다.
        - 결과 라벨을 safeguard_label로 반환한다.
        - PASS가 아닌 경우 error_code를 설정하는 정책을 정의한다.
        - 라벨별 사용자 메시지/차단 정책을 문서화한다.
        - SafeguardLabel/ErrorCode(Enum)을 사용해 값을 고정한다.
    """
    logger = logging.getLogger(__name__)
    user_input = state.get("last_user_message", "")
    prompt = SAFEGUARD_PROMPT.format(user_input=user_input)

    raw_output = _call_openai(prompt)
    label = _normalize_label(raw_output)

    result = {"safeguard_label": label}
    if raw_output == "":
        result["error_code"] = ErrorCode.MODEL
        logger.warning("안전 분류 모델 응답이 비어 있습니다.")
    return result


def _call_openai(prompt: str) -> str:
    """OpenAI Chat Completions API로 안전 분류를 수행한다."""
    if not prompt:
        return ""
    if not _OPENAI_API_KEY:
        return ""

    headers = {
        "Authorization": f"Bearer {_OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": _DEFAULT_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }
    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.post(_API_URL, headers=headers, json=payload)
            response.raise_for_status()
    except httpx.HTTPError:
        return ""

    data = response.json()
    choices = data.get("choices", [])
    if not choices:
        return ""
    message = choices[0].get("message", {})
    return (message.get("content") or "").strip()


def _normalize_label(raw_output: str) -> SafeguardLabel:
    """모델 출력에서 안전 라벨을 정규화한다."""
    cleaned = raw_output.strip().upper()
    if cleaned == SafeguardLabel.PASS.value:
        return SafeguardLabel.PASS
    if cleaned == SafeguardLabel.PII.value:
        return SafeguardLabel.PII
    if cleaned == SafeguardLabel.HARMFUL.value:
        return SafeguardLabel.HARMFUL
    if cleaned == SafeguardLabel.PROMPT_INJECTION.value:
        return SafeguardLabel.PROMPT_INJECTION
    return SafeguardLabel.PASS
