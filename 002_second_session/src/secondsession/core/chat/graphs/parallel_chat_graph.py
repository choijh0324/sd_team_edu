# 목적: 병렬 대화 그래프 예제를 제공한다.
# 설명: 팬아웃/팬인 구조로 병렬 결과를 합류한다.
# 디자인 패턴: Pipeline, Fan-out/Fan-in
# 참조: docs/01_langgraph_to_service/04_병렬_그래프_설계.md

"""병렬 대화 그래프 구성 모듈."""

import os
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from langgraph.graph import StateGraph, END

from secondsession.core.chat.const.error_code import ErrorCode
from secondsession.core.chat.state.chat_state import ChatState

_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
_DEFAULT_MODEL = "gpt-4o-mini"
_API_URL = "https://api.openai.com/v1/chat/completions"
# 병렬 호출 비용 상한 정책(팀 기준):
# - 후보 생성은 최대 2개로 제한한다.
# - 추가 후보가 필요하면 운영 승인 후 확장한다.
# - 동일 요청에서 병렬 호출 수는 2회를 넘지 않는다.


@dataclass(frozen=True)
class QuorumPolicy:
    """병렬 결과 합류 기준을 정의한다."""

    required_success: int

    def is_acceptable(self, successes: int) -> bool:
        """성공 개수가 기준을 만족하는지 확인한다."""
        return successes >= self.required_success


@dataclass(frozen=True)
class BarrierPolicy:
    """필수 결과 키 준비 여부를 검사한다."""

    required_keys: set[str]

    def is_ready(self, results: dict[str, str]) -> bool:
        """필수 결과 키가 모두 존재하는지 확인한다."""
        return self.required_keys.issubset(results.keys())


def build_parallel_chat_graph(checkpointer) -> object:
    """병렬 대화 그래프를 생성한다.

    Args:
        checkpointer: LangGraph 체크포인터 인스턴스.

    Returns:
        object: 컴파일된 LangGraph 애플리케이션.
    """
    graph = StateGraph(ChatState)

    graph.add_node("fanout", _wrap_node("fanout", _fanout_node, checkpointer))
    graph.add_node("candidate_a", _wrap_node("candidate_a", _candidate_a_node, checkpointer))
    graph.add_node("candidate_b", _wrap_node("candidate_b", _candidate_b_node, checkpointer))
    graph.add_node("merge", _wrap_node("merge", _merge_candidates_node, checkpointer))

    graph.set_entry_point("fanout")
    graph.add_edge("fanout", "candidate_a")
    graph.add_edge("fanout", "candidate_b")
    graph.add_edge("candidate_a", "merge")
    graph.add_edge("candidate_b", "merge")
    graph.add_edge("merge", END)

    return graph.compile(checkpointer=checkpointer)


def _wrap_node(node_name: str, handler, checkpointer):
    """노드 실행 후 체크포인트를 저장하는 래퍼."""

    def _wrapped(state: ChatState) -> dict:
        updated = handler(state)
        snapshot = dict(state)
        if isinstance(updated, dict):
            snapshot.update(updated)
        thread_id = snapshot.get("thread_id")
        if thread_id and hasattr(checkpointer, "save"):
            checkpointer.save(
                thread_id=thread_id,
                state=snapshot,
                metadata={
                    "node": node_name,
                    "route": snapshot.get("route"),
                    "error_code": snapshot.get("error_code"),
                    "safeguard_label": snapshot.get("safeguard_label"),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        return updated

    return _wrapped


def _fanout_node(state: ChatState) -> dict:
    """팬아웃 진입 노드."""
    return {}


def _candidate_a_node(state: ChatState) -> dict:
    """후보 답변 A를 생성한다(간결 우선)."""
    user_message = state.get("last_user_message", "")
    prompt = (
        "당신은 친절한 서비스 어시스턴트입니다.\n"
        "[규칙]\n"
        "- 한두 문장으로 간결하게 답변하세요.\n"
        "- 불필요한 추측은 피하세요.\n\n"
        f"[사용자 입력]\n{user_message}\n\n[출력]\n"
        "답변만 출력하세요."
    )
    output = _call_openai(prompt)
    return {"candidate_a": output}


def _candidate_b_node(state: ChatState) -> dict:
    """후보 답변 B를 생성한다(설명 우선)."""
    user_message = state.get("last_user_message", "")
    prompt = (
        "당신은 친절한 서비스 어시스턴트입니다.\n"
        "[규칙]\n"
        "- 핵심을 유지하면서 간단한 배경 설명을 포함하세요.\n"
        "- 불필요한 추측은 피하세요.\n\n"
        f"[사용자 입력]\n{user_message}\n\n[출력]\n"
        "답변만 출력하세요."
    )
    output = _call_openai(prompt)
    return {"candidate_b": output}


def _merge_candidates_node(state: ChatState) -> dict:
    """후보를 합류해 최종 답변을 선택한다."""
    candidate_a = (state.get("candidate_a") or "").strip()
    candidate_b = (state.get("candidate_b") or "").strip()

    results = {
        "candidate_a": candidate_a,
        "candidate_b": candidate_b,
    }
    barrier = BarrierPolicy(required_keys={"candidate_a", "candidate_b"})
    if not barrier.is_ready(results):
        return {
            "last_assistant_message": "",
            "error_code": ErrorCode.ROUTING,
        }

    successes = sum(bool(c) for c in [candidate_a, candidate_b])
    if not QuorumPolicy(required_success=1).is_acceptable(successes):
        return {
            "last_assistant_message": "",
            "error_code": ErrorCode.MODEL,
        }

    user_message = state.get("last_user_message", "")
    score_a = _score_candidate(user_message, candidate_a)
    score_b = _score_candidate(user_message, candidate_b)
    best = candidate_a if score_a >= score_b else candidate_b
    return {"last_assistant_message": best}


def _score_candidate(user_message: str, candidate: str) -> int:
    """간단한 정합성/가독성 점수로 후보를 비교한다."""
    if not candidate:
        return -10_000

    score = 0
    length = len(candidate)
    if 40 <= length <= 600:
        score += 3
    if 10 <= length < 40:
        score += 1
    if length > 600:
        score -= 2

    # 질문과의 단어 겹침(아주 단순한 정합성 신호)
    user_tokens = {token for token in user_message.split() if len(token) >= 2}
    candidate_tokens = {token for token in candidate.split() if len(token) >= 2}
    overlap = len(user_tokens & candidate_tokens)
    score += min(overlap, 3)

    # 종결 부호가 있으면 가독성 가점
    if candidate.endswith((".", "!", "?", "요", "다")):
        score += 1

    return score


def _call_openai(prompt: str) -> str:
    """OpenAI Chat Completions API로 답변 후보를 생성한다."""
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
        "temperature": 0.3,
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
