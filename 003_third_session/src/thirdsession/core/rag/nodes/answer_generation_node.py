# 목적: 근거 기반 최종 답변을 생성한다.
# 설명: 질문과 검색 컨텍스트를 입력받아 LLM 기반으로 답변을 합성한다.
# 디자인 패턴: Command
# 참조: thirdsession/core/rag/prompts/answer_prompt.py, rag_pipeline_graph.py

"""근거 기반 답변 생성 노드 모듈."""

from __future__ import annotations

import asyncio
from threading import Thread
from typing import Any

from langchain_core.output_parsers import StrOutputParser

from thirdsession.core.common.llm_client import LlmClient
from thirdsession.core.rag.prompts.answer_prompt import ANSWER_PROMPT


class AnswerGenerationNode:
    """근거 기반 답변 생성 노드."""

    def __init__(self, llm_client: LlmClient | None = None) -> None:
        """노드 의존성을 초기화한다.

        Args:
            llm_client: 답변 생성에 사용할 LLM 클라이언트(선택).
        """
        self._llm_client = llm_client

    def run(self, question: str, contexts: list[Any]) -> tuple[str, bool]:
        """질문과 컨텍스트로 최종 답변을 생성한다.

        Returns:
            tuple[str, bool]: (답변 텍스트, LLM 생성 사용 여부)
        """
        formatted_contexts = self._format_contexts(contexts)
        if formatted_contexts.strip() == "":
            return "", False

        if self._llm_client is None:
            return self._fallback_answer(question=question, contexts=contexts), False

        try:
            chain = ANSWER_PROMPT | self._llm_client.chat_model() | StrOutputParser()
            answer = self._run_async(
                asyncio.to_thread(
                    chain.invoke,
                    {
                        "question": question,
                        "contexts": formatted_contexts,
                    },
                ),
            )
            normalized = " ".join(str(answer).split())
            if normalized == "":
                return self._fallback_answer(question=question, contexts=contexts), False
            return normalized, True
        except Exception:
            return self._fallback_answer(question=question, contexts=contexts), False

    def _format_contexts(self, contexts: list[Any]) -> str:
        """컨텍스트 목록을 프롬프트 입력 문자열로 변환한다."""
        lines: list[str] = []
        for index, context in enumerate(contexts, start=1):
            if isinstance(context, dict):
                text = str(context.get("content") or context.get("page_content") or "").strip()
                source_id = context.get("source_id") or context.get("id") or f"source-{index}"
            else:
                text = str(getattr(context, "page_content", "") or str(context)).strip()
                metadata = getattr(context, "metadata", None)
                if isinstance(metadata, dict):
                    source_id = metadata.get("source_id") or metadata.get("id") or f"source-{index}"
                else:
                    source_id = f"source-{index}"
            if text == "":
                continue
            lines.append(f"[{source_id}] {text}")
        return "\n".join(lines)

    def _fallback_answer(self, question: str, contexts: list[Any]) -> str:
        """LLM 사용 불가 시 최소한의 근거 기반 답변을 생성한다."""
        if not contexts:
            return "관련 근거를 찾지 못해 답변을 제공하기 어렵습니다."
        summary_points: list[str] = []
        for context in contexts[:3]:
            if isinstance(context, dict):
                text = str(context.get("content") or context.get("page_content") or "").strip()
                source_id = str(context.get("source_id") or context.get("id") or "")
            else:
                text = str(getattr(context, "page_content", "") or str(context)).strip()
                metadata = getattr(context, "metadata", None)
                source_id = str(metadata.get("source_id")) if isinstance(metadata, dict) else ""
            if text == "":
                continue
            citation = f"[{source_id}] " if source_id else ""
            summary_points.append(f"- {citation}{' '.join(text.split())[:140]}")
        if not summary_points:
            return "관련 근거를 찾지 못해 답변을 제공하기 어렵습니다."
        return f"질문: {question}\n근거 기반 요약:\n" + "\n".join(summary_points)

    def _run_async(self, coroutine: Any) -> Any:
        """동기 컨텍스트에서 코루틴을 안전하게 실행한다."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coroutine)

        result_box: dict[str, Any] = {}
        error_box: dict[str, Exception] = {}

        def runner() -> None:
            try:
                result_box["result"] = asyncio.run(coroutine)
            except Exception as error:  # pragma: no cover
                error_box["error"] = error

        thread = Thread(target=runner, daemon=True)
        thread.start()
        thread.join()

        if "error" in error_box:
            raise error_box["error"]
        return result_box.get("result")
