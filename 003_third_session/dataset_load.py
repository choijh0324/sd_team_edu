""" 
목적: Hugging Face 데이터셋을 pgvector 테이블에 적재한다.
설명: 데이터 로드 -> 텍스트 추출/청킹 -> 임베딩 -> PostgreSQL upsert를 수행한다.
디자인 패턴: 파이프라인(Pipeline)
참조: src/thirdsession/core/rag/graphs/rag_pipeline_graph.py, docs/01_pgvector_vector_search/*
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from typing import Any, Iterable

from dotenv import load_dotenv
from psycopg import connect


@dataclass(frozen=True)
class ChunkDocument:
    """적재 대상 청크 문서 모델."""

    source_id: str
    title: str
    content: str
    metadata: dict[str, Any]


def parse_args() -> argparse.Namespace:
    """실행 인자를 파싱한다."""
    parser = argparse.ArgumentParser(description="Hugging Face 데이터셋을 pgvector에 적재한다.")
    parser.add_argument("--dataset", default="rag-datasets/rag-mini-wikipedia", help="Hugging Face 데이터셋 ID")
    parser.add_argument("--config", default="question-answer", help="데이터셋 config 이름")
    parser.add_argument("--split", default="test", help="데이터셋 split 이름")
    parser.add_argument("--limit", type=int, default=300, help="원본 문서 최대 개수")
    parser.add_argument("--chunk-size", type=int, default=800, help="청크 길이(문자)")
    parser.add_argument("--chunk-overlap", type=int, default=120, help="청크 오버랩(문자)")
    parser.add_argument("--table", default="rag_documents", help="적재 테이블명")
    return parser.parse_args()


def main() -> None:
    """데이터셋 적재 파이프라인을 실행한다."""
    load_dotenv()
    args = parse_args()

    pg_dsn = require_env("PG_DSN")
    google_api_key = require_env("GOOGLE_API_KEY")
    embedding_model = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")

    rows = load_hf_rows(
        dataset_name=args.dataset,
        dataset_config=args.config,
        split=args.split,
        limit=args.limit,
    )
    documents = build_chunk_documents(
        rows=rows,
        dataset_name=args.dataset,
        dataset_config=args.config,
        split=args.split,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )
    if not documents:
        raise ValueError("적재할 문서가 없습니다. 데이터셋 필드 추출 규칙을 확인하세요.")

    embeddings = embed_texts(
        texts=[doc.content for doc in documents],
        google_api_key=google_api_key,
        model_name=embedding_model,
    )
    if len(embeddings) != len(documents):
        raise RuntimeError("임베딩 개수와 문서 개수가 일치하지 않습니다.")

    upsert_documents(
        dsn=pg_dsn,
        table_name=args.table,
        documents=documents,
        embeddings=embeddings,
    )
    print(f"[완료] 문서 {len(documents)}건을 {args.table} 테이블에 적재했습니다.")


def require_env(name: str) -> str:
    """필수 환경 변수를 조회한다."""
    value = os.getenv(name)
    if value is None or value.strip() == "":
        raise ValueError(f"{name} 환경 변수가 필요합니다.")
    return value


def load_hf_rows(
    dataset_name: str,
    dataset_config: str,
    split: str,
    limit: int,
) -> list[dict[str, Any]]:
    """Hugging Face 데이터셋에서 행을 로드한다."""
    try:
        from datasets import load_dataset
    except ImportError as error:
        raise ImportError(
            "datasets 패키지가 필요합니다. `uv add datasets` 후 다시 실행하세요."
        ) from error

    dataset = load_dataset(dataset_name, dataset_config, split=split)
    rows: list[dict[str, Any]] = []
    for idx, item in enumerate(dataset):
        if idx >= limit:
            break
        rows.append(dict(item))
    return rows


def build_chunk_documents(
    rows: Iterable[dict[str, Any]],
    dataset_name: str,
    dataset_config: str,
    split: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[ChunkDocument]:
    """원본 행을 청크 문서 목록으로 변환한다."""
    documents: list[ChunkDocument] = []
    safe_overlap = max(0, min(chunk_overlap, chunk_size - 1))

    for row_index, row in enumerate(rows):
        title = extract_title(row, default_title=f"untitled-{row_index}")
        content = extract_text(row)
        if content.strip() == "":
            continue
        chunks = split_text(content, chunk_size=chunk_size, chunk_overlap=safe_overlap)
        base_source_id = (
            str(row.get("id"))
            if row.get("id") is not None
            else f"{dataset_name}:{dataset_config}:{split}:{row_index}"
        )
        for chunk_index, chunk in enumerate(chunks):
            source_id = f"{base_source_id}:{chunk_index}"
            metadata = {
                "dataset": dataset_name,
                "config": dataset_config,
                "split": split,
                "row_index": row_index,
                "chunk_index": chunk_index,
                "title": title,
            }
            documents.append(
                ChunkDocument(
                    source_id=source_id,
                    title=title,
                    content=chunk,
                    metadata=metadata,
                )
            )
    return documents


def extract_title(row: dict[str, Any], default_title: str) -> str:
    """행에서 제목을 추출한다."""
    candidate_keys = ["title", "article_title", "wiki_title", "page_title"]
    for key in candidate_keys:
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return default_title


def extract_text(row: dict[str, Any]) -> str:
    """행에서 본문 텍스트를 추출한다."""
    for key in ["text", "content", "context", "article", "passage", "document"]:
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    question = row.get("question")
    answer = row.get("answer")
    if isinstance(question, str) and isinstance(answer, str):
        merged = f"Q: {question}\nA: {answer}".strip()
        if merged:
            return merged
    answers = row.get("answers")
    if isinstance(answers, dict):
        text_candidates = answers.get("text")
        if isinstance(text_candidates, list) and text_candidates:
            joined = "\n".join(str(item) for item in text_candidates if str(item).strip())
            if joined.strip():
                return joined.strip()
    if isinstance(answers, list):
        joined = "\n".join(str(item) for item in answers if str(item).strip())
        if joined.strip():
            return joined.strip()
    return ""


def split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """문자 단위 슬라이딩 윈도우로 청킹한다."""
    normalized = " ".join(text.split())
    if not normalized:
        return []
    if len(normalized) <= chunk_size:
        return [normalized]

    chunks: list[str] = []
    step = max(1, chunk_size - chunk_overlap)
    start = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(normalized):
            break
        start += step
    return chunks


def embed_texts(texts: list[str], google_api_key: str, model_name: str) -> list[list[float]]:
    """Google 임베딩 모델로 텍스트 임베딩을 생성한다."""
    try:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
    except ImportError as error:
        raise ImportError(
            "langchain-google-genai 패키지가 필요합니다. `uv sync` 후 다시 실행하세요."
        ) from error

    os.environ.setdefault("GOOGLE_API_KEY", google_api_key)
    embedder = GoogleGenerativeAIEmbeddings(model=model_name)
    return embedder.embed_documents(texts)


def upsert_documents(
    dsn: str,
    table_name: str,
    documents: list[ChunkDocument],
    embeddings: list[list[float]],
) -> None:
    """pgvector 테이블을 생성하고 문서를 upsert한다."""
    vector_dim = len(embeddings[0])
    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id BIGSERIAL PRIMARY KEY,
        source_id TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
        embedding VECTOR({vector_dim}) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """
    create_index_sql = f"""
    CREATE INDEX IF NOT EXISTS idx_{table_name}_embedding
    ON {table_name}
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
    """
    upsert_sql = f"""
    INSERT INTO {table_name} (source_id, title, content, metadata, embedding)
    VALUES (%s, %s, %s, %s::jsonb, %s::vector)
    ON CONFLICT (source_id)
    DO UPDATE SET
        title = EXCLUDED.title,
        content = EXCLUDED.content,
        metadata = EXCLUDED.metadata,
        embedding = EXCLUDED.embedding;
    """

    with connect(dsn) as conn:
        with conn.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cursor.execute(create_table_sql)
            if vector_dim <= 2000:
                cursor.execute(create_index_sql)
            else:
                print(
                    "[안내] 임베딩 차원이 2000을 초과하여 ivfflat 인덱스를 생성하지 않습니다. "
                    "RAG 동작 확인에는 문제없지만, 검색 성능은 느릴 수 있습니다."
                )
            for doc, embedding in zip(documents, embeddings):
                cursor.execute(
                    upsert_sql,
                    (
                        doc.source_id,
                        doc.title,
                        doc.content,
                        json.dumps(doc.metadata, ensure_ascii=False),
                        to_vector_literal(embedding),
                    ),
                )
        conn.commit()


def to_vector_literal(values: list[float]) -> str:
    """float 배열을 PostgreSQL vector 리터럴 문자열로 변환한다."""
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"


if __name__ == "__main__":
    main()
