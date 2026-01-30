# 목적: 대화 요약 노드를 정의한다.
# 설명: 대화 내역을 요약해 summary에 저장한다.
# 디자인 패턴: 커맨드
# 참조: secondsession/core/chat/graphs/chat_graph.py

"""대화 요약 노드 모듈."""

import os

import httpx

from secondsession.core.chat.const.error_code import ErrorCode
from secondsession.core.chat.state.chat_state import ChatState
from secondsession.core.chat.prompts.summary_prompt import SUMMARY_PROMPT

_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
_DEFAULT_MODEL = "gpt-4o-mini"
_API_URL = "https://api.openai.com/v1/chat/completions"


def summary_node(state: ChatState) -> dict:
    """대화 요약을 생성한다.

    TODO:
        - LLM 클라이언트를 연결한다.
        - SUMMARY_PROMPT.format으로 state["history"]를 결합한다.
        - summary 값을 반환한다.
    """
    history = state.get("history", [])
    summary_input = _build_summary_input(history)
    prompt = SUMMARY_PROMPT.format(chat_history=summary_input)
    summary = _call_openai(prompt)
    if not summary:
        return {
            "summary": "",
            "error_code": ErrorCode.MODEL,
        }
    return {"summary": summary}


def _build_summary_input(history: list[dict]) -> str:
    """요약 입력 문자열을 만든다."""
    return "\n".join([f"{m.get('role')}: {m.get('content')}" for m in history])


def _call_openai(prompt: str) -> str:
    """OpenAI Chat Completions API로 요약을 생성한다."""
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
    except httpx.HTTPError:
        return ""
    data = response.json()
    choices = data.get("choices", [])
    if not choices:
        return ""
    message = choices[0].get("message", {})
    return (message.get("content") or "").strip()
