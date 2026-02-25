# 목적: PostgreSQL(pgvector) 기반 검색기를 제공한다.
# 설명: 질의를 임베딩한 뒤 벡터 유사도 검색으로 문서를 반환한다.
# 디자인 패턴: Repository + Adapter
# 참조: dataset_load.py, thirdsession/core/rag/graphs/rag_pipeline_graph.py

"""pgvector 검색기 모듈."""

from __future__ import annotations

import asyncio
import os
import re
from typing import Any

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from psycopg import connect


class PgVectorRetriever:
    """pgvector 테이블을 조회하는 검색기."""

    _SAFE_IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

    def __init__(
        self,
        dsn: str,
        table_name: str,
        google_api_key: str,
        embedding_model: str = "gemini-embedding-001",
        default_k: int = 5,
        default_collection: str | None = None,
        timeout_seconds: float = 10.0,
        embedder: GoogleGenerativeAIEmbeddings | None = None,
    ) -> None:
        """검색기 의존성을 초기화한다.

        Args:
            dsn: PostgreSQL DSN 문자열.
            table_name: 검색 대상 테이블명.
            google_api_key: 임베딩 생성용 Google API 키.
            embedding_model: 임베딩 모델명.
            default_k: 기본 검색 개수.
            default_collection: 기본 컬렉션 필터(선택).
            timeout_seconds: DB 커넥션 타임아웃(초).
            embedder: 재사용할 임베더 인스턴스(선택).
        """
        if not self._SAFE_IDENTIFIER.match(table_name):
            raise ValueError("table_name은 영문/숫자/언더스코어만 허용됩니다.")
        if google_api_key.strip() == "":
            raise ValueError("google_api_key는 빈 값일 수 없습니다.")

        self._dsn = dsn
        self._table_name = table_name
        self._embedding_model = embedding_model
        self._default_k = max(1, default_k)
        self._default_collection = default_collection
        self._timeout_seconds = max(0.1, timeout_seconds)
        os.environ.setdefault("GOOGLE_API_KEY", google_api_key)
        self._embedder = embedder or GoogleGenerativeAIEmbeddings(model=embedding_model)

    def for_request(self, top_k: int | None = None, collection: str | None = None) -> "PgVectorRetriever":
        """요청별 검색 옵션을 반영한 검색기 인스턴스를 반환한다."""
        return PgVectorRetriever(
            dsn=self._dsn,
            table_name=self._table_name,
            google_api_key=os.getenv("GOOGLE_API_KEY", ""),
            embedding_model=self._embedding_model,
            default_k=top_k if isinstance(top_k, int) and top_k > 0 else self._default_k,
            default_collection=collection if collection is not None else self._default_collection,
            timeout_seconds=self._timeout_seconds,
            embedder=self._embedder,
        )

    def invoke(self, query: str) -> list[dict[str, Any]]:
        """질의를 동기 검색한다."""
        return self.similarity_search(query=query, k=self._default_k, collection=self._default_collection)

    async def ainvoke(self, query: str) -> list[dict[str, Any]]:
        """질의를 비동기 검색한다."""
        return await asyncio.to_thread(self.invoke, query)

    def similarity_search(
        self,
        query: str,
        k: int | None = None,
        collection: str | None = None,
    ) -> list[dict[str, Any]]:
        """질의 유사 문서를 조회한다."""
        normalized_query = query.strip()
        if normalized_query == "":
            return []

        search_k = k if isinstance(k, int) and k > 0 else self._default_k
        search_collection = collection if collection is not None else self._default_collection
        query_vector = self._embedder.embed_query(normalized_query)
        vector_literal = self._to_vector_literal(query_vector)

        where_sql = ""
        params: list[Any] = [vector_literal]
        if isinstance(search_collection, str) and search_collection.strip() != "":
            where_sql = (
                "WHERE COALESCE(metadata->>'collection', metadata->>'dataset', '') = %s "
                "OR source_id ILIKE %s "
                "OR title ILIKE %s "
            )
            collection_value = search_collection.strip()
            like_value = f"%{collection_value}%"
            params.extend([collection_value, like_value, like_value])

        sql = (
            f"SELECT source_id, title, content, metadata, (embedding <=> %s::vector) AS distance "
            f"FROM {self._table_name} "
            f"{where_sql}"
            "ORDER BY embedding <=> %s::vector "
            "LIMIT %s"
        )
        params.extend([vector_literal, search_k])

        with connect(self._dsn, connect_timeout=int(self._timeout_seconds)) as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()

        docs: list[dict[str, Any]] = []
        for source_id, title, content, metadata, distance in rows:
            docs.append(
                {
                    "source_id": str(source_id),
                    "title": str(title) if title is not None else None,
                    "content": str(content) if content is not None else "",
                    "metadata": metadata if isinstance(metadata, dict) else {},
                    "score": float(distance) if isinstance(distance, (int, float)) else 0.0,
                    "score_type": "distance",
                }
            )
        return docs

    def _to_vector_literal(self, values: list[float]) -> str:
        """float 배열을 vector 리터럴 문자열로 변환한다."""
        return "[" + ",".join(f"{value:.8f}" for value in values) + "]"
