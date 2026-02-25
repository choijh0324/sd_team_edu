# 목적: RAG 검색기 패키지를 초기화한다.
# 설명: 벡터 검색 어댑터를 외부에 노출한다.
# 디자인 패턴: 파사드
# 참조: thirdsession/core/rag/retrieval/pgvector_retriever.py

"""RAG 검색기 패키지."""

from thirdsession.core.rag.retrieval.pgvector_retriever import PgVectorRetriever

__all__ = ["PgVectorRetriever"]
