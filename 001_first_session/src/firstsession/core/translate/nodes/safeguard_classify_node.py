# 목적: 입력 문장을 안전 분류로 라우팅한다.
# 설명: PASS/PII/HARMFUL/PROMPT_INJECTION 라벨로 안전 여부를 판정한다.
# 디자인 패턴: 전략 패턴 + 파이프라인 노드
# 참조: docs/04_string_tricks/02_single_choice_파서.md

"""안전 분류 노드 모듈."""

from __future__ import annotations

import re

from firstsession.core.translate.nodes.call_model_node import CallModelNode
from firstsession.core.translate.prompts.safeguard_prompt import SAFEGUARD_PROMPT
from firstsession.core.translate.state.translation_state import TranslationState


class SafeguardClassifyNode:
    """안전 분류를 담당하는 노드."""

    def run(self, state: TranslationState) -> TranslationState:
        """입력에 대한 안전 라벨을 판정한다.

        Args:
            state: 현재 번역 상태.

        Returns:
            TranslationState: 안전 라벨이 포함된 상태.
        """
        user_input = state.get("normalized_text") or state.get("text", "")
        prompt = SAFEGUARD_PROMPT.format(user_input=user_input)
        raw_output = CallModelNode().run(prompt)
        label = self._normalize_label(raw_output)

        updated_state = dict(state)
        updated_state["safeguard_label"] = label
        return updated_state

    def _normalize_label(self, raw_output: str) -> str:
        """모델 출력에서 안전 라벨을 정규화한다."""
        cleaned = raw_output.strip().upper()
        if cleaned in {"PASS", "PII", "HARMFUL", "PROMPT_INJECTION"}:
            return cleaned
        return "PASS"

    # def _looks_like_prompt_injection(self, text: str) -> bool:
    #     """프롬프트 인젝션 시도를 감지한다."""
    #     lowered = text.lower()
    #     keyword_pairs = [
    #         ("ignore", "instruction"),
    #         ("system", "prompt"),
    #         ("developer", "message"),
    #         ("override", "rule"),
    #         ("bypass", "policy"),
    #         ("jailbreak", ""),
    #         ("prompt injection", ""),
    #         ("reveal", "secret"),
    #         ("api", "key"),
    #         ("access", "token"),
    #         ("password", ""),
    #         ("규칙", "무시"),
    #         ("시스템", "무시"),
    #         ("프롬프트", "무시"),
    #         ("지침", "무시"),
    #         ("정책", "우회"),
    #         ("보안", "우회"),
    #         ("비밀", "노출"),
    #         ("키", "노출"),
    #         ("토큰", "노출"),
    #     ]
    #     for first, second in keyword_pairs:
    #         if first in lowered and (not second or second in lowered):
    #             return True
    #     return False

    # def _looks_harmful(self, text: str) -> bool:
    #     """유해/위험 행동 관련 요청을 감지한다."""
    #     harmful_keywords = [
    #         "자해",
    #         "자살",
    #         "폭력",
    #         "살인",
    #         "공격",
    #         "테러",
    #         "폭탄",
    #         "무기",
    #         "마약",
    #         "해킹",
    #         "범죄",
    #         "협박",
    #         "혐오",
    #         "차별",
    #     ]
    #     return any(keyword in text for keyword in harmful_keywords)

    # def _looks_like_pii(self, text: str) -> bool:
    #     """개인정보 포함 여부를 감지한다."""
    #     if re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text):
    #         return True
    #     if re.search(r"\b\d{6}-?\d{7}\b", text):
    #         return True
    #     if re.search(r"\b01[016789][-.\s]?\d{3,4}[-.\s]?\d{4}\b", text):
    #         return True
    #     if re.search(r"\b\d{3}[-.\s]?\d{3,4}[-.\s]?\d{4}\b", text):
    #         return True
    #     pii_keywords = [
    #         "전화번호",
    #         "이메일",
    #         "주소",
    #         "주민등록",
    #         "계좌",
    #         "카드번호",
    #         "신용카드",
    #         "여권",
    #         "비밀번호",
    #     ]
    #     return any(keyword in text for keyword in pii_keywords)
