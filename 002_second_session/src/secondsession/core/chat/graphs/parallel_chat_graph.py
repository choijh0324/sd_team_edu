# 목적: 병렬 대화 그래프 예제를 제공한다.
# 설명: 팬아웃/팬인 구조로 병렬 결과를 합류한다.
# 디자인 패턴: 파이프라인 + 빌더
# 참조: docs/01_langgraph_to_service/04_병렬_그래프_설계.md

"""병렬 대화 그래프 구성 모듈."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from secondsession.core.chat.const import ErrorCode
from secondsession.core.chat.nodes.fallback_node import FallbackNode
from secondsession.core.chat.prompts.answer_prompt import ANSWER_PROMPT
from secondsession.core.chat.state.chat_state import ChatState
from secondsession.core.common.app_config import AppConfig
from secondsession.core.common.llm_client import LlmClient


class ParallelChatGraph:
    """병렬 대화 그래프 실행기."""

    def __init__(
        self,
        checkpointer: Any | None = None,
        llm_client: LlmClient | None = None,
    ) -> None:
        """그래프를 초기화한다.

        Args:
            checkpointer: LangGraph 체크포인터 인스턴스.
            llm_client: LLM 클라이언트(선택).
        """
        self._checkpointer = checkpointer
        self._llm_client = llm_client
        self._app = self._build_graph()

    def run(self, state: ChatState) -> ChatState:
        """병렬 대화 그래프를 실행한다.

        Args:
            state: 대화 입력 상태.

        Returns:
            ChatState: 대화 결과 상태.
        """
        config = self._build_config(state)
        if config is None:
            return self._app.invoke(state)
        return self._app.invoke(state, config)

    def _build_config(self, state: ChatState) -> dict | None:
        """체크포인터 복구를 위한 실행 설정을 구성한다."""
        thread_id = state.get("thread_id")
        if not thread_id:
            return None
        configurable: dict[str, str] = {"thread_id": str(thread_id)}
        checkpoint_id = state.get("checkpoint_id")
        if checkpoint_id:
            configurable["checkpoint_id"] = str(checkpoint_id)
        return {"configurable": configurable}

    def _build_graph(self) -> object:
        """병렬 대화 그래프를 구성한다.

        Returns:
            object: 컴파일된 LangGraph 애플리케이션.

        구현 내용:
            - 팬아웃에서 후보 A/B를 병렬 생성한다.
            - 팬인에서 후보를 합류하고 최종 답변을 선택한다.
            - 쿼럼은 1개 성공 시 합류로 설정한다.
            - 실패 시 fallback으로 전환하고 error_code를 설정한다.
            - 선택 기준은 길이 점수 기반으로 한다.
            - thread_id 복구 정책을 적용한다.
        """
        graph = StateGraph(ChatState)
        fallback_node = FallbackNode()

        graph.add_node("fanout", self._fanout)
        graph.add_node("candidate_a", self._candidate_a)
        graph.add_node("candidate_b", self._candidate_b)
        graph.add_node("join", self._join_candidates)
        graph.add_node("fallback", fallback_node.run)

        graph.set_entry_point("fanout")
        graph.add_edge("fanout", "candidate_a")
        graph.add_edge("fanout", "candidate_b")
        graph.add_edge("candidate_a", "join")
        graph.add_edge("candidate_b", "join")

        graph.add_conditional_edges("join", lambda s: s["route"], {
            "end": END,
            "fallback": "fallback",
        })
        graph.add_edge("fallback", END)

        if self._checkpointer is None:
            return graph.compile()
        return graph.compile(checkpointer=self._checkpointer)

    def _fanout(self, state: ChatState) -> ChatState:
        """팬아웃 시작 노드."""
        _ = state
        return {}

    def _candidate_a(self, state: ChatState) -> ChatState:
        """후보 A를 생성한다."""
        return self._generate_candidate(state, variant="A")

    def _candidate_b(self, state: ChatState) -> ChatState:
        """후보 B를 생성한다."""
        return self._generate_candidate(state, variant="B")

    def _generate_candidate(self, state: ChatState, variant: str) -> ChatState:
        """후보 응답을 생성하고 점수를 계산한다."""
        user_message = state.get("last_user_message", "")
        llm = self._get_llm()
        prompt = self._build_variant_prompt(user_message, variant)
        try:
            result = llm.invoke(prompt)
        except Exception:
            return {"candidate_errors": [ErrorCode.MODEL.code]}
        content = str(getattr(result, "content", result)).strip()
        if not content:
            return {"candidate_errors": [ErrorCode.VALIDATION.code]}
        score = self._score_candidate(content)
        return {
            "candidates": [content],
            "candidate_scores": [score],
        }

    def _join_candidates(self, state: ChatState) -> ChatState:
        """후보를 합류하고 최종 답변을 선택한다."""
        candidates = state.get("candidates", [])
        scores = state.get("candidate_scores", [])
        pairs = list(zip(candidates, scores))
        if not pairs:
            return {
                "route": "fallback",
                "error_code": ErrorCode.MODEL,
            }
        best = max(pairs, key=lambda item: item[1])
        return {
            "route": "end",
            "selected_candidate": best[0],
            "last_assistant_message": best[0],
        }

    def _build_variant_prompt(self, user_message: str, variant: str) -> str:
        """후보별 프롬프트를 구성한다."""
        base = ANSWER_PROMPT.format(user_message=user_message)
        if variant == "B":
            return f"{base}\n\n[변형]\n핵심만 간단히 bullet로 답변하세요."
        return f"{base}\n\n[변형]\n간결하고 실무적인 톤으로 답변하세요."

    def _score_candidate(self, content: str) -> float:
        """후보 점수를 계산한다."""
        return float(len(content))

    def _get_llm(self):
        """LLM 인스턴스를 반환한다."""
        if self._llm_client is None:
            config = AppConfig.from_env()
            self._llm_client = LlmClient(config)
        return self._llm_client.chat_model()
