# 목적: 서비스 계층의 공통 SSE 유틸리티를 제공한다.
# 설명: SSE 직렬화/역직렬화와 DONE 이벤트 생성을 일관되게 처리한다.
# 디자인 패턴: Utility
# 참조: thirdsession/api/rag/service/rag_service.py, rag_job_service.py

"""SSE 유틸리티 모듈."""

from __future__ import annotations

from typing import Any

from thirdsession.core.common.sse_utils import done_sse_line, parse_sse_line, to_sse_line

__all__ = ["to_sse_line", "parse_sse_line", "done_sse_line"]
