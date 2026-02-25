# 목적: FastAPI 애플리케이션 진입점을 제공한다.
# 설명: uvicorn에서 "thirdsession.main:app" 형태로 실행할 수 있는 앱 객체를 정의한다.
# 디자인 패턴: 팩토리 메서드 패턴(애플리케이션 생성 책임 분리)
# 참조: thirdsession/api, thirdsession/core

"""FastAPI 애플리케이션 진입점 모듈."""

import logging

from fastapi import FastAPI

from thirdsession.api.rag.service.rag_job_service import RagJobService
from thirdsession.api.rag.router import register_rag_routes
from thirdsession.api.rag.service.rag_service import RagService
from thirdsession.core.rag.graphs.rag_pipeline_graph import RagPipelineGraph
from thirdsession.core.common.app_config import AppConfig
from thirdsession.core.common.llm_client import LlmClient
from thirdsession.core.rag.retrieval import PgVectorRetriever


LOGGER = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """FastAPI 애플리케이션을 생성한다.

    Returns:
        FastAPI: 구성된 애플리케이션 인스턴스.
    """
    app = FastAPI(title="thirdsession API")

    config = AppConfig.from_env()
    llm_client = LlmClient(config)
    retriever = _build_retriever(config)
    graph = RagPipelineGraph(llm_client=llm_client, retriever=retriever, store=retriever)
    rag_service = RagService(graph)
    job_service = RagJobService(graph=graph, llm_client=llm_client)
    app.state.rag_service = rag_service
    app.state.job_service = job_service
    register_rag_routes(app)

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        """간단한 헬스 체크 엔드포인트."""
        return {"status": "ok"}

    return app


def _build_retriever(config: AppConfig) -> PgVectorRetriever | None:
    """환경 설정을 기반으로 pgvector 검색기를 생성한다."""
    if config.pg_dsn is None or config.pg_dsn.strip() == "":
        LOGGER.warning("PG_DSN이 없어 RAG 검색기를 비활성화합니다.")
        return None
    try:
        return PgVectorRetriever(
            dsn=config.pg_dsn,
            table_name=config.rag_table,
            google_api_key=config.google_api_key,
            embedding_model=config.embedding_model,
            default_k=config.rag_top_k,
        )
    except Exception:
        LOGGER.exception("pgvector 검색기 생성에 실패해 검색 없이 동작합니다.")
        return None


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("thirdsession.main:app", host="0.0.0.0", port=8000, reload=True)
