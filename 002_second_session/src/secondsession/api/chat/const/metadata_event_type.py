# 목적: 메타데이터 이벤트 타입을 정의한다.
# 설명: 메타데이터 이벤트 이름을 Enum으로 고정한다.
# 디자인 패턴: Value Object
# 참조: secondsession/api/chat/model/chat_stream_metadata.py

"""메타데이터 이벤트 타입 상수 모듈."""

from enum import Enum


class MetadataEventType(Enum):
    """메타데이터 이벤트 타입."""

    NODE_START = "node_start"
    NODE_END = "node_end"
    ROUTE_DECISION = "route_decision"
    FALLBACK = "fallback"
    WARNING = "warning"
    JOB_QUEUED = "job_queued"
    JOB_START = "job_start"
    JOB_END = "job_end"
    JOB_ERROR = "job_error"
