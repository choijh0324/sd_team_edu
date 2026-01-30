# 목적: 사용자 입력에 대한 답변을 생성한다.
# 설명: LLM 호출을 통해 응답을 만든다.
# 디자인 패턴: 커맨드
# 참조: secondsession/core/chat/graphs/chat_graph.py

"""대화 응답 생성 노드 모듈."""

import os
import logging

import httpx
from pydantic import BaseModel, Field, ValidationError

from secondsession.core.chat.const.error_code import ErrorCode
from secondsession.core.chat.const import (
    build_context,
    get_context_budget_by_model,
    trim_by_budget,
    trim_keep_system_and_tool,
)
from secondsession.core.chat.prompts.answer_prompt import ANSWER_PROMPT
from secondsession.core.chat.state.chat_state import ChatState

_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
_DEFAULT_MODEL = "gpt-4o-mini"
_API_URL = "https://api.openai.com/v1/chat/completions"


class AnswerOutput(BaseModel):
    """답변 출력 스키마."""

    message: str = Field(..., min_length=1, max_length=2000)


def answer_node(state: ChatState) -> dict:
    """사용자 입력에 대한 답변을 생성한다.

    TODO:
        - LLM 클라이언트를 연결한다.
        - ANSWER_PROMPT.format으로 사용자 입력을 결합한다.
        - state["last_user_message"]를 기반으로 답변을 생성한다.
        - 결과를 last_assistant_message로 반환한다.
        - 응답 스키마(Pydantic) 검증 실패 시 error_code를 설정한다.
        - 도구 호출 실패/타임아웃 시 error_code를 설정한다.
        - error_code가 설정된 경우 폴백 라우팅 흐름을 고려한다.
        - ErrorCode(Enum)로 에러 유형을 고정한다.
    """
    user_message = state.get("last_user_message", "")
    logger = logging.getLogger(__name__)
    history = state.get("history", [])
    summary = state.get("summary")
    budget = get_context_budget_by_model(_DEFAULT_MODEL)
    trimmed = trim_keep_system_and_tool(history, keep_last=6)
    recent_messages = trim_by_budget(trimmed, budget=budget)
    logger.info(
        "트리밍 결과: before=%s, after=%s, budget=%s",
        len(history),
        len(recent_messages),
        budget,
    )
    context_messages = build_context(summary, recent_messages)
    context_text = "\n".join(
        f"{m.get('role')}: {m.get('content')}" for m in context_messages
    )
    prompt = ANSWER_PROMPT.format(user_message=f"{context_text}\n{user_message}")

    raw_output = _call_openai(prompt)
    if raw_output == "":
        return {
            "last_assistant_message": "",
            "error_code": ErrorCode.MODEL,
        }

    try:
        validated = AnswerOutput.model_validate({"message": raw_output})
    except ValidationError:
        return {
            "last_assistant_message": "",
            "error_code": ErrorCode.VALIDATION,
        }

    return {"last_assistant_message": validated.message}


def _call_openai(prompt: str) -> str:
    """OpenAI Chat Completions API로 답변을 생성한다."""
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
        "temperature": 0.2,
    }
    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.post(_API_URL, headers=headers, json=payload)
            response.raise_for_status()
    except httpx.TimeoutException:
        return ""
    except httpx.HTTPError:
        return ""

    data = response.json()
    choices = data.get("choices", [])
    if not choices:
        return ""
    message = choices[0].get("message", {})
    return (message.get("content") or "").strip()
