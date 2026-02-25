# 목적: 서비스 수준 RAG 파이프라인 그래프를 정의한다.
# 설명: 검색 → 정규화 → 병합 → 후처리 → 생성 → 스트리밍 순서를 담는다.
# 디자인 패턴: 파이프라인 + 빌더
# 참조: thirdsession/core/rag/nodes/postprocess_node.py

"""RAG 파이프라인 그래프 모듈."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from thirdsession.core.common.llm_client import LlmClient
from thirdsession.core.rag.const import ErrorCode, SafeguardLabel
from thirdsession.core.rag.graphs.adaptive_hyde_graph import AdaptiveHydeGraph
from thirdsession.core.rag.graphs.query_decompose_graph import QueryDecomposeGraph
from thirdsession.core.rag.nodes.answer_generation_node import AnswerGenerationNode
from thirdsession.core.rag.nodes.decide_summary_node import DecideSummaryNode
from thirdsession.core.rag.nodes.fallback_node import FallbackNode
from thirdsession.core.rag.nodes.postprocess_node import PostprocessNode
from thirdsession.core.rag.nodes.safeguard_node import SafeguardNode
from thirdsession.core.rag.nodes.summary_node import SummaryNode
from thirdsession.core.rag.state.chat_state import ChatState


class RagPipelineGraph:
    """RAG 파이프라인 그래프."""

    def __init__(
        self,
        llm_client: LlmClient | None = None,
        retriever: Any | None = None,
        store: Any | None = None,
    ) -> None:
        """그래프 의존성을 초기화한다.

        Args:
            llm_client: LLM 클라이언트(선택).
            retriever: 질의 분해 검색기(선택).
            store: HyDE 검색용 벡터 스토어(선택).
        """
        self._llm_client = llm_client
        self._retriever = retriever
        self._store = store
        self._safeguard_node = SafeguardNode()
        self._postprocess_node = PostprocessNode()
        self._fallback_node = FallbackNode()
        self._answer_generation_node = AnswerGenerationNode(llm_client=llm_client)
        self._decide_summary_node = DecideSummaryNode(summary_threshold=5)
        self._summary_node = SummaryNode(llm_client=llm_client)
        self._query_decompose_graph = QueryDecomposeGraph(llm_client=llm_client, retriever=retriever)
        self._adaptive_hyde_graph = AdaptiveHydeGraph(llm_client=llm_client, store=store)
        self._compiled_graph = self._build_graph()

    def run(self, state: ChatState) -> ChatState:
        """RAG 파이프라인을 실행한다.

        Args:
            state: 입력 상태.

        Returns:
            ChatState: 실행 결과 상태.
        """
        base_state = dict(state)
        # run 이전 최소 기본값을 채워 TypedDict 필수 키 누락을 방지한다.
        base_state.setdefault("history", [])
        base_state.setdefault("summary", None)
        base_state.setdefault("turn_count", 0)
        base_state.setdefault("contexts", [])
        base_state.setdefault("answer", None)
        base_state.setdefault("last_user_message", base_state.get("question"))
        base_state.setdefault("last_assistant_message", None)
        base_state.setdefault("route", None)
        base_state.setdefault("error_code", None)
        base_state.setdefault("safeguard_label", None)
        base_state.setdefault("trace_id", None)
        base_state.setdefault("thread_id", None)
        base_state.setdefault("session_id", None)
        base_state.setdefault("user_id", None)
        base_state.setdefault("metadata", {})
        base_state.setdefault("sources", [])
        base_state.setdefault("retrieval_stats", None)
        result = self._compiled_graph.invoke(base_state)
        return result

    def _build_graph(self) -> Any:
        """그래프를 구성한다.

        Returns:
            Any: LangGraph 애플리케이션.
        """
        graph = StateGraph(ChatState)
        graph.add_node("safeguard", self._node_safeguard)
        graph.add_node("retrieve", self._node_retrieve)
        graph.add_node("policy_filter", self._node_policy_filter)
        graph.add_node("normalize", self._node_normalize)
        graph.add_node("merge", self._node_merge)
        graph.add_node("postprocess", self._node_postprocess)
        graph.add_node("generate", self._node_generate)
        graph.add_node("summary", self._node_summary)
        graph.set_entry_point("safeguard")
        graph.add_edge("safeguard", "retrieve")
        graph.add_edge("retrieve", "policy_filter")
        graph.add_edge("policy_filter", "normalize")
        graph.add_edge("normalize", "merge")
        graph.add_edge("merge", "postprocess")
        graph.add_edge("postprocess", "generate")
        graph.add_conditional_edges(
            "generate",
            self._should_run_summary,
            {True: "summary", False: END},
        )
        graph.add_edge("summary", END)
        return graph.compile()

    def _node_safeguard(self, state: ChatState) -> dict[str, Any]:
        """입력 안전 분류를 수행한다."""
        question = state["question"]
        try:
            label = self._safeguard_node.run(question)
            safeguard_label = label.value if isinstance(label, SafeguardLabel) else str(label)
        except NotImplementedError:
            safeguard_label = self._fallback_safeguard(question)
        except Exception:
            safeguard_label = SafeguardLabel.PASS.value
        return {"safeguard_label": safeguard_label}

    def _node_retrieve(self, state: ChatState) -> dict[str, Any]:
        """검색 전략 그래프를 실행해 컨텍스트 후보를 모은다."""
        question = state["question"]
        metadata = state.get("metadata") or {}
        top_k = self._resolve_top_k(metadata)
        collection = self._resolve_collection(metadata)
        retriever = metadata.get("retriever") or self._retriever
        store = metadata.get("store") or self._store
        retriever = self._with_request_options(retriever, top_k=top_k, collection=collection)
        store = self._with_request_options(store, top_k=top_k, collection=collection)

        try:
            query_docs = self._query_decompose_graph.run(question=question, retriever=retriever)
            hyde_docs = self._adaptive_hyde_graph.run(question=question, store=store)
        except Exception as error:
            mapped_error = ErrorCode.from_exception(error)
            return {
                "contexts": [],
                "route": "retrieve_failed",
                "error_code": mapped_error.code,
            }
        return {
            "contexts": query_docs + hyde_docs,
            "route": "query_decompose+adaptive_hyde",
        }

    def _with_request_options(self, target: Any, top_k: int, collection: str | None) -> Any:
        """검색 대상 객체에 요청 옵션을 주입한다."""
        if target is None:
            return None
        if hasattr(target, "for_request"):
            try:
                return target.for_request(top_k=top_k, collection=collection)
            except Exception:
                return target
        return target

    def _resolve_top_k(self, metadata: dict[str, Any]) -> int:
        """요청 메타데이터에서 top_k를 안전하게 추출한다."""
        raw = metadata.get("top_k")
        if isinstance(raw, int) and raw > 0:
            return raw
        return 5

    def _resolve_collection(self, metadata: dict[str, Any]) -> str | None:
        """요청 메타데이터에서 컬렉션 필터를 추출한다."""
        raw = metadata.get("collection")
        if isinstance(raw, str) and raw.strip() != "":
            return raw.strip()
        return None

    def _node_policy_filter(self, state: ChatState) -> dict[str, Any]:
        """정책 기반 사전 필터를 적용한다."""
        contexts = state.get("contexts", [])
        user_metadata = state.get("metadata") or {}
        allowed_language = user_metadata.get("language")

        filtered: list[Any] = []
        for doc in contexts:
            metadata = self._doc_metadata(doc)
            access_level = metadata.get("access_level")
            if access_level not in {None, "public"}:
                continue
            if allowed_language is not None and metadata.get("language") not in {None, allowed_language}:
                continue
            filtered.append(doc)
        return {"contexts": filtered}

    def _node_normalize(self, state: ChatState) -> dict[str, Any]:
        """score_type(distance/similarity)을 similarity로 통일한다."""
        contexts = state.get("contexts", [])
        normalized: list[dict[str, Any]] = []
        for doc in contexts:
            source = self._to_doc_dict(doc)
            raw_score = source.get("score")
            score_type = str(source.get("score_type") or "similarity")
            if isinstance(raw_score, (int, float)):
                score = float(raw_score)
                if score_type == "distance":
                    score = 1.0 / (1.0 + max(score, 0.0))
            else:
                score = 0.0
            source["score"] = score
            source["score_type"] = "similarity"
            normalized.append(source)
        return {"contexts": normalized}

    def _node_merge(self, state: ChatState) -> dict[str, Any]:
        """정규화된 결과를 병합/중복 제거한다."""
        contexts = state.get("contexts", [])
        deduped: list[dict[str, Any]] = []
        seen: set[str] = set()
        for doc in contexts:
            key = str(doc.get("source_id") or doc.get("doc_id") or doc.get("id") or doc.get("content"))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(doc)
        deduped.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
        return {"contexts": deduped}

    def _node_postprocess(self, state: ChatState) -> dict[str, Any]:
        """후처리 노드를 실행하고 실패 시 폴백 규칙을 적용한다."""
        contexts = state.get("contexts", [])
        try:
            processed = self._postprocess_node.run(contexts)
        except NotImplementedError:
            processed = self._fallback_postprocess(contexts)
        except Exception:
            processed = self._fallback_postprocess(contexts)
        return {"contexts": processed}

    def _node_generate(self, state: ChatState) -> dict[str, Any]:
        """최종 답변/근거를 생성한다."""
        contexts = state.get("contexts", [])
        question = state["question"]
        safeguard_label = state.get("safeguard_label")

        if safeguard_label in {SafeguardLabel.PII.value, SafeguardLabel.HARMFUL.value, SafeguardLabel.PROMPT_INJECTION.value}:
            if safeguard_label == SafeguardLabel.PII.value:
                error_code = ErrorCode.PII
            elif safeguard_label == SafeguardLabel.HARMFUL.value:
                error_code = ErrorCode.HARMFUL
            else:
                error_code = ErrorCode.PROMPT_INJECTION
            answer = self._fallback_node.run(error_code)
            return {
                "answer": answer,
                "sources": [],
                "error_code": error_code.code,
                "retrieval_stats": {"retrieved": len(contexts), "used": 0},
                "history": [
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": answer},
                ],
                "turn_count": 1,
                "last_user_message": question,
                "last_assistant_message": answer,
            }

        if len(contexts) == 0:
            state_error = ErrorCode.from_code(state.get("error_code"))
            error_code = state_error if state.get("error_code") else ErrorCode.RETRIEVAL_EMPTY
            answer = self._fallback_node.run(error_code)
            return {
                "answer": answer,
                "sources": [],
                "error_code": error_code.code,
                "retrieval_stats": {"retrieved": 0, "used": 0},
                "history": [
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": answer},
                ],
                "turn_count": 1,
                "last_user_message": question,
                "last_assistant_message": answer,
            }

        answer, used_llm_generation = self._answer_generation_node.run(question=question, contexts=contexts)
        if answer.strip() == "":
            answer = self._fallback_node.run(ErrorCode.LLM_FAILED)
            return {
                "answer": answer,
                "sources": [],
                "error_code": ErrorCode.LLM_FAILED.code,
                "retrieval_stats": {"retrieved": len(contexts), "used": 0},
                "history": [
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": answer},
                ],
                "turn_count": 1,
                "last_user_message": question,
                "last_assistant_message": answer,
            }

        sources = [self._to_source_item(doc, index) for index, doc in enumerate(contexts, start=1)]
        error_code = None if used_llm_generation else ErrorCode.LLM_FAILED.code
        return {
            "answer": answer,
            "sources": sources,
            "error_code": error_code,
            "retrieval_stats": {"retrieved": len(contexts), "used": len(sources)},
            "history": [
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer},
            ],
            "turn_count": 1,
            "last_user_message": question,
            "last_assistant_message": answer,
        }

    def _should_run_summary(self, state: ChatState) -> bool:
        """요약 노드 실행 여부를 판정한다."""
        return self._decide_summary_node.run(int(state.get("turn_count", 0)))

    def _node_summary(self, state: ChatState) -> dict[str, Any]:
        """대화 이력을 요약해 상태에 반영한다."""
        history = state.get("history", [])
        previous_summary = state.get("summary")
        summary = self._summary_node.run(history=history, previous_summary=previous_summary)
        return {"summary": summary}

    def _fallback_safeguard(self, question: str) -> str:
        """안전 분류 노드 미구현 시 사용할 간단 규칙 기반 판정."""
        lowered = question.lower()
        blocked_keywords = ["주민번호", "비밀번호", "신용카드", "폭탄", "악성코드", "프롬프트 인젝션"]
        if any(keyword in lowered for keyword in blocked_keywords):
            return SafeguardLabel.HARMFUL.value
        return SafeguardLabel.PASS.value

    def _fallback_postprocess(self, docs: list[Any]) -> list[Any]:
        """후처리 노드 미구현 시 사용할 기본 후처리."""
        candidates = [self._to_doc_dict(doc) for doc in docs]
        # source_id 기준 중복 제거
        deduped: list[dict[str, Any]] = []
        seen: set[str] = set()
        for candidate in candidates:
            key = str(candidate.get("source_id") or candidate.get("doc_id") or candidate.get("id") or candidate.get("content"))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(candidate)

        # 간단 재정렬 + 상위 5개 제한
        deduped.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
        return deduped[:5]

    def _compose_grounded_answer(self, question: str, contexts: list[Any]) -> str:
        """근거 기반 답변 텍스트를 구성한다."""
        bullets: list[str] = []
        for doc in contexts[:3]:
            content = self._doc_content(doc)
            if content == "":
                continue
            compact = " ".join(content.split())
            bullets.append(f"- {compact[:160]}")
        if not bullets:
            return self._fallback_node.run(ErrorCode.RETRIEVAL_EMPTY)
        return f"질문: {question}\n근거 기반 요약:\n" + "\n".join(bullets)

    def _to_source_item(self, doc: Any, index: int) -> dict[str, Any]:
        """응답용 source 항목을 생성한다."""
        data = self._to_doc_dict(doc)
        source_id = data.get("source_id") or data.get("doc_id") or data.get("id") or f"source-{index}"
        return {
            "source_id": str(source_id),
            "title": data.get("title"),
            "snippet": (data.get("content") or data.get("snippet") or "")[:300],
            "score": data.get("score"),
            "metadata": data.get("metadata"),
        }

    def _to_doc_dict(self, doc: Any) -> dict[str, Any]:
        """문서 타입을 공통 dict로 변환한다."""
        if isinstance(doc, dict):
            metadata = doc.get("metadata")
            if metadata is None:
                metadata = {}
            return {
                "doc_id": doc.get("doc_id"),
                "id": doc.get("id"),
                "source_id": doc.get("source_id"),
                "title": doc.get("title"),
                "content": doc.get("content") or doc.get("page_content") or "",
                "snippet": doc.get("snippet"),
                "score": doc.get("score", 0.0),
                "score_type": doc.get("score_type", "similarity"),
                "metadata": metadata,
            }

        metadata = getattr(doc, "metadata", None)
        if metadata is None:
            metadata = {}
        page_content = getattr(doc, "page_content", None)
        return {
            "doc_id": getattr(doc, "doc_id", None),
            "id": getattr(doc, "id", None),
            "source_id": metadata.get("source_id") if isinstance(metadata, dict) else None,
            "title": metadata.get("title") if isinstance(metadata, dict) else None,
            "content": page_content or str(doc),
            "snippet": None,
            "score": metadata.get("score", 0.0) if isinstance(metadata, dict) else 0.0,
            "score_type": metadata.get("score_type", "similarity") if isinstance(metadata, dict) else "similarity",
            "metadata": metadata if isinstance(metadata, dict) else {},
        }

    def _doc_metadata(self, doc: Any) -> dict[str, Any]:
        """문서 메타데이터를 반환한다."""
        return self._to_doc_dict(doc).get("metadata", {})

    def _doc_content(self, doc: Any) -> str:
        """문서 본문 텍스트를 반환한다."""
        return str(self._to_doc_dict(doc).get("content", ""))
