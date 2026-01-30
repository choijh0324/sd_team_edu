# 목적: 번역 처리를 LangGraph로 구성한다.
# 설명: 입력 → 안전 분류 → 번역 → QC → 재번역 → 응답 흐름을 연결한다.
# 디자인 패턴: 파이프라인 + 빌더
# 참조: docs/04_string_tricks/01_yes_no_파서.md, docs/04_string_tricks/02_single_choice_파서.md

"""번역 그래프 구성 모듈."""

import logging

from langgraph.graph import END, StateGraph

from firstsession.core.translate.state.translation_state import TranslationState
from firstsession.core.translate.nodes.normalize_input_node import NormalizeInputNode
from firstsession.core.translate.nodes.postprocess_node import PostprocessNode
from firstsession.core.translate.nodes.quality_check_node import QualityCheckNode
from firstsession.core.translate.nodes.response_node import ResponseNode
from firstsession.core.translate.nodes.retry_gate_node import RetryGateNode
from firstsession.core.translate.nodes.retry_translate_node import RetryTranslateNode
from firstsession.core.translate.nodes.safeguard_classify_node import SafeguardClassifyNode
from firstsession.core.translate.nodes.safeguard_decision_node import SafeguardDecisionNode
from firstsession.core.translate.nodes.safeguard_fail_response_node import (
    SafeguardFailResponseNode,
)
from firstsession.core.translate.nodes.translate_node import TranslateNode


class TranslateGraph:
    """번역 그래프 실행기."""

    def __init__(self) -> None:
        """그래프를 초기화한다."""
        self._logger = logging.getLogger(__name__)
        self._graph = self._build_graph().compile()

    def run(self, state: TranslationState) -> TranslationState:
        """번역 그래프를 실행한다.

        Args:
            state: 번역 입력 상태.

        Returns:
            TranslationState: 번역 결과 상태.
        """
        self._logger.info("그래프 시작 상태: %s", state)
        result = self._graph.invoke(state)
        self._logger.info("그래프 종료 상태: %s", result)
        return result

    def _build_graph(self) -> StateGraph:
        """번역 그래프를 구성한다.

        Returns:
            StateGraph: 구성된 그래프.
        """
        graph = StateGraph(TranslationState)

<<<<<<< HEAD
        graph.add_node(
            "normalize_input",
            self._wrap_node("normalize_input", NormalizeInputNode().run),
        )
        graph.add_node(
            "safeguard_classify",
            self._wrap_node("safeguard_classify", SafeguardClassifyNode().run),
        )
        graph.add_node(
            "safeguard_decision",
            self._wrap_node("safeguard_decision", SafeguardDecisionNode().run),
        )
        graph.add_node(
            "safeguard_fail_response",
            self._wrap_node(
                "safeguard_fail_response",
                SafeguardFailResponseNode().run,
            ),
        )
        graph.add_node(
            "translate",
            self._wrap_node("translate", TranslateNode().run),
        )
        graph.add_node(
            "postprocess",
            self._wrap_node("postprocess", PostprocessNode().run),
        )
        graph.add_node(
            "quality_check",
            self._wrap_node("quality_check", QualityCheckNode().run),
        )
        graph.add_node(
            "retry_gate",
            self._wrap_node("retry_gate", RetryGateNode().run),
        )
        graph.add_node(
            "retry_translate",
            self._wrap_node("retry_translate", RetryTranslateNode().run),
        )
        graph.add_node(
            "response",
            self._wrap_node("response", ResponseNode().run),
        )
=======
        # TODO: START 노드에서 시작하는 흐름을 명시한다.
        # - START -> NormalizeInputNode
        # TODO: 노드 등록 방식은 두 가지 모두 가능하다.
        # - 함수형: graph.add_node("normalize", normalize_input)
        # - 클래스형: graph.add_node("normalize", self.normalize_input_node.run)
        #   - 클래스형은 무상태로 설계하고, 공유 데이터는 state에만 기록한다.
        # TODO: 다음 노드들을 추가하고 엣지를 연결한다.
        # - NormalizeInputNode: 입력 정규화
        # - SafeguardClassifyNode: PASS/PII/HARMFUL/PROMPT_INJECTION 판정
        # - SafeguardDecisionNode: PASS 여부 기록 및 오류 메시지 세팅
        # - SafeguardFailResponseNode: 차단 응답 구성
        # - TranslateNode: 번역 수행
        # - QualityCheckNode: 번역 품질 YES/NO 판정
        # - RetryGateNode: 재번역 가능 여부 판단
        # - RetryTranslateNode: 재번역 수행
        # - ResponseNode: 최종 응답 구성
>>>>>>> origin/main

        graph.set_entry_point("normalize_input")
        graph.add_edge("normalize_input", "safeguard_classify")
        graph.add_edge("safeguard_classify", "safeguard_decision")
        graph.add_conditional_edges(
            "safeguard_decision",
            self._route_safeguard,
            {
                "pass": "translate",
                "fail": "safeguard_fail_response",
            },
        )
        graph.add_edge("safeguard_fail_response", "response")
        graph.add_edge("translate", "postprocess")
        graph.add_edge("postprocess", "quality_check")
        graph.add_edge("quality_check", "retry_gate")
        graph.add_conditional_edges(
            "retry_gate",
            self._route_retry,
            {
                "pass": "response",
                "retry": "retry_translate",
                "fail": "response",
            },
        )
        graph.add_edge("retry_translate", "postprocess")
        graph.add_edge("response", END)

        return graph

    def _wrap_node(self, name: str, handler):
        """노드 실행 전후로 상태를 로깅하는 래퍼를 생성한다."""

        def _wrapped(state: TranslationState) -> TranslationState:
            self._logger.info("노드 진입: %s, 상태=%s", name, state)
            result = handler(state)
            self._logger.info("노드 종료: %s, 상태=%s", name, result)
            return result

        return _wrapped

    def _route_safeguard(self, state: TranslationState) -> str:
        """안전 분류 결과에 따라 다음 경로를 선택한다."""
        label = state.get("safeguard_label", "")
        return "pass" if label == "PASS" else "fail"

    def _route_retry(self, state: TranslationState) -> str:
        """품질 검사 결과와 재시도 횟수로 다음 경로를 선택한다."""
        qc_passed = state.get("qc_passed", "")
        if qc_passed == "YES":
            return "pass"

        retry_count = int(state.get("retry_count", 0) or 0)
        max_retry_count = int(state.get("max_retry_count", 3) or 3)
        if retry_count < max_retry_count:
            return "retry"
        return "fail"
