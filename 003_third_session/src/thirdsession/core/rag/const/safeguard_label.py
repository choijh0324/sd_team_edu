# 목적: 안전 분류 라벨을 정의한다.
# 설명: 안전 분기 정책에서 일관된 라벨을 사용한다.
# 디자인 패턴: Value Object
# 참조: nextStep.md

"""안전 분류 라벨 상수 모듈."""

from enum import Enum
from typing import Any


class SafeguardLabel(Enum):
    """안전 분류 라벨."""

    PASS = "PASS"
    PII = "PII"
    HARMFUL = "HARMFUL"
    PROMPT_INJECTION = "PROMPT_INJECTION"


class SafeguardAction(Enum):
    """안전 라벨 대응 액션."""

    ALLOW = "allow"
    BLOCK = "block"
    REDIRECT = "redirect"
    MASK = "mask"


SAFEGUARD_POLICIES: dict[SafeguardLabel, dict[str, Any]] = {
    SafeguardLabel.PASS: {
        "action": SafeguardAction.ALLOW,
        "reason": "정상 요청",
        "http_status": 200,
    },
    SafeguardLabel.PII: {
        "action": SafeguardAction.MASK,
        "reason": "개인정보 보호 필요",
        "http_status": 200,
    },
    SafeguardLabel.HARMFUL: {
        "action": SafeguardAction.BLOCK,
        "reason": "유해 요청 차단",
        "http_status": 403,
    },
    SafeguardLabel.PROMPT_INJECTION: {
        "action": SafeguardAction.REDIRECT,
        "reason": "프롬프트 인젝션 의심",
        "http_status": 400,
    },
}


def policy_for(label: SafeguardLabel) -> dict[str, Any]:
    """라벨에 대응하는 정책 정보를 반환한다."""
    return SAFEGUARD_POLICIES.get(label, SAFEGUARD_POLICIES[SafeguardLabel.PROMPT_INJECTION])


def action_for(label: SafeguardLabel) -> SafeguardAction:
    """라벨에 대응하는 액션을 반환한다."""
    policy = policy_for(label)
    action = policy.get("action")
    if isinstance(action, SafeguardAction):
        return action
    return SafeguardAction.BLOCK
