# 목적: 애플리케이션 공통 로깅 설정을 제공한다.
# 설명: 콘솔/파일 핸들러를 동시에 구성하고 중복 설정을 방지한다.
# 디자인 패턴: 팩토리 메서드 패턴
# 참조: fourthsession/main.py, fourthsession/mcp/mcp_server.py

"""공통 로깅 설정 모듈."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path


_IS_CONFIGURED = False


def configure_logging(service_name: str = "fourthsession") -> None:
    """애플리케이션 로깅을 초기화한다.

    Args:
        service_name (str): 로그 레코드에 표시할 서비스 이름.
    """
    global _IS_CONFIGURED
    if _IS_CONFIGURED:
        return

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_dir = _resolve_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / os.getenv("LOG_FILE_NAME", f"{service_name}.log")

    formatter = logging.Formatter(
        fmt=(
            "%(asctime)s | %(levelname)s | %(name)s | "
            "%(threadName)s | %(message)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=int(os.getenv("LOG_MAX_BYTES", str(5 * 1024 * 1024))),
        backupCount=int(os.getenv("LOG_BACKUP_COUNT", "5")),
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    _IS_CONFIGURED = True


def _resolve_log_dir() -> Path:
    """로그 디렉터리 경로를 계산한다."""
    env_log_dir = os.getenv("LOG_DIR")
    if env_log_dir:
        return Path(env_log_dir)

    current = Path(__file__).resolve()
    for parent in current.parents:
        if parent.name == "src":
            return parent.parent / "logs"
    return current.parent / "logs"
