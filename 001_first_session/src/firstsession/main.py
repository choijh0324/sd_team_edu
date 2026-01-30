# 목적: FastAPI 애플리케이션 진입점을 제공한다.
# 설명: uvicorn에서 \"firstsession.main:app\" 형태로 실행할 수 있는 앱 객체를 정의한다.
# 디자인 패턴: 팩토리 메서드 패턴(애플리케이션 생성 책임 분리)
# 참조: firstsession/api, firstsession/core

"""FastAPI 애플리케이션 진입점 모듈."""

import logging
import os
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI

from firstsession.api.translate.router.translate_router import TranslateRouter
from firstsession.api.translate.service.translation_service import TranslationService
from firstsession.core.translate.graphs.translate_graph import TranslateGraph


def _configure_logging() -> None:
    """로그 설정을 초기화한다."""
    os.makedirs("logs", exist_ok=True)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s - %(message)s"
    )
    file_handler = RotatingFileHandler(
        "logs/firstsession.log",
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)


def create_app() -> FastAPI:
    """FastAPI 애플리케이션을 생성한다.

    Returns:
        FastAPI: 구성된 애플리케이션 인스턴스.
    """
    _configure_logging()
    app = FastAPI(title="firstsession API")

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        """간단한 헬스 체크 엔드포인트."""
        return {"status": "ok"}

    graph = TranslateGraph()
    service = TranslationService(graph)
    translate_router = TranslateRouter(service)
    app.include_router(translate_router.router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("firstsession.main:app", host="0.0.0.0", port=8000, reload=True)
