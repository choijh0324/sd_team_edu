# 목적: 안전 분류 라벨을 정의한다.
# 설명: 안전 분기 정책에서 일관된 라벨을 사용한다.
# 디자인 패턴: Value Object
# 참조: secondsession/core/chat/prompts/safeguard_prompt.py

"""안전 분류 라벨 상수 모듈."""

from enum import Enum


class SafeguardLabel(Enum):
    """안전 분류 라벨."""

    PASS = "PASS"
    PII = "PII"
    HARMFUL = "HARMFUL"
    PROMPT_INJECTION = "PROMPT_INJECTION"


# 라벨 정책:
# - PASS: 정상 처리
# - PII: 차단 + 안전 안내(개인정보 보호 목적)
# - HARMFUL: 차단 + 안전 안내(자해/폭력/범죄 등)
# - PROMPT_INJECTION: 차단 + 보안 경고(규칙 무력화/권한 상승 시도)
