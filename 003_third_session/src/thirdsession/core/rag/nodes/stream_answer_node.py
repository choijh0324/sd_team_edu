# 목적: 답변 생성과 스트리밍을 수행한다.
# 설명: 근거 기반 답변을 만든 뒤 토큰 단위 스트리밍 규칙을 적용한다.
# 디자인 패턴: Command
# 참조: thirdsession/core/rag/prompts/answer_prompt.py, thirdsession/api/rag/model/chat_stream_event.py

"""답변 생성/스트리밍 노드 모듈."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
import re
from typing import Any

from langchain_core.output_parsers import StrOutputParser

from thirdsession.core.common.llm_client import LlmClient
from thirdsession.core.common.sse_utils import to_sse_line
from thirdsession.core.rag.prompts.answer_prompt import ANSWER_PROMPT

# TODO: 스트리밍 이벤트 모델/타입을 활용하도록 연결한다.


class StreamAnswerNode:
    """답변 생성/스트리밍 노드."""

    def __init__(self, llm_client: LlmClient | None = None) -> None:
        """노드 의존성을 초기화한다.

        Args:
            llm_client: LLM 클라이언트(선택).
        """
        self._llm_client = llm_client

    async def run(
        self,
        question: str,
        contexts: list[Any],
        trace_id: str,
        seq_start: int = 1,
        node: str | None = "stream_answer",
        prebuilt_answer: str | None = None,
    ) -> AsyncIterator[str]:
        """답변을 생성한 뒤 스트리밍한다.

        Args:
            question: 사용자 질문.
            contexts: 검색/후처리된 컨텍스트.
            trace_id: 스트리밍 추적 식별자.
            seq_start: 시작 시퀀스 번호.
            node: 노드 식별자(선택).

        Yields:
            str: SSE 데이터 라인.
        """
        answer = prebuilt_answer if isinstance(prebuilt_answer, str) else await self._generate_answer(question, contexts)
        tokens = self._split_answer(answer)
        _ = trace_id
        _ = node

        index = seq_start
        for token in tokens:
            yield self._to_sse_line(
                {
                    "type": "token",
                    "status": "in_progress",
                    "content": token,
                    "index": index,
                }
            )
            index += 1

        yield self._to_sse_line(
            {
                "type": "token",
                "status": "end",
                "content": "",
            }
        )

    async def _generate_answer(self, question: str, contexts: list[Any]) -> str:
        """근거 기반 답변을 생성한다."""
        formatted_contexts = self._format_contexts(contexts)
        if formatted_contexts.strip() == "":
            return "관련 근거를 찾지 못해 답변을 제공하기 어렵습니다."

        if self._llm_client is None:
            return self._fallback_answer(question=question, contexts=contexts)

        try:
            chain = ANSWER_PROMPT | self._llm_client.chat_model() | StrOutputParser()
            return await asyncio.to_thread(
                chain.invoke,
                {
                    "question": question,
                    "contexts": formatted_contexts,
                },
            )
        except Exception:
            return self._fallback_answer(question=question, contexts=contexts)

    def _split_answer(self, answer: str) -> list[str]:
        """답변을 토큰 단위로 분리한다."""
        cleaned = answer.strip()
        if cleaned == "":
            return []
        # 공백을 유지해 클라이언트에서 원문을 복원할 수 있게 한다.
        return re.findall(r"\S+\s*", cleaned)

    def _format_contexts(self, contexts: list[Any]) -> str:
        """컨텍스트 목록을 LLM 입력 문자열로 변환한다."""
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
        """LLM 미사용/실패 시 사용할 기본 답변을 생성한다."""
        if not contexts:
            return "관련 근거를 찾지 못해 답변을 제공하기 어렵습니다."
        summary_points: list[str] = []
        for context in contexts[:3]:
            if isinstance(context, dict):
                text = str(context.get("content") or context.get("page_content") or "").strip()
            else:
                text = str(getattr(context, "page_content", "") or str(context)).strip()
            if text == "":
                continue
            summary_points.append(f"- {' '.join(text.split())[:120]}")
        if not summary_points:
            return "관련 근거를 찾지 못해 답변을 제공하기 어렵습니다."
        return f"질문: {question}\n근거 기반 요약:\n" + "\n".join(summary_points)

    def _to_sse_line(self, payload: dict[str, Any]) -> str:
        """SSE 라인 문자열로 직렬화한다."""
        return to_sse_line(payload)
