# 목적: 안전 분류 라벨을 정의한다.
# 설명: 안전 분기 정책에서 일관된 라벨을 사용한다.
# 디자인 패턴: Value Object
# 참조: secondsession/core/chat/prompts/safeguard_prompt.py

"""안전 분류 라벨 상수 모듈."""

from enum import Enum


class SafeguardLabel(Enum):
    """안전 분류 라벨."""

    # 라벨 정책
    # - PASS: 정상 처리
    # - PII: 개인정보 포함 가능성 → 차단 + 안전 안내
    # - HARMFUL: 유해/위험 요청 → 차단 + 안전 안내
    # - PROMPT_INJECTION: 보안 우회 시도 → 차단 + 보안 경고
    PASS = "PASS"
    PII = "PII"
    HARMFUL = "HARMFUL"
    PROMPT_INJECTION = "PROMPT_INJECTION"


# TODO:
# - 라벨별 정책(차단/완화/리다이렉트)을 문서화한다.
