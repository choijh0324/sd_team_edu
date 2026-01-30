# 목적: 대화 요약 프롬프트 템플릿을 제공한다.
# 설명: 요약 품질을 높이기 위한 기본 프롬프트를 정의한다.
# 디자인 패턴: Singleton
# 참조: secondsession/core/chat/nodes/summary_node.py

"""대화 요약 프롬프트 모듈."""

from textwrap import dedent

from langchain_core.prompts import PromptTemplate

_SUMMARY_PROMPT = dedent(
    """\
당신은 대화 요약 전문가입니다.

[규칙]
- 핵심 정보만 추려서 간결하게 요약하세요.
- 불필요한 수식은 제거하고 사실 중심으로 정리하세요.
- 5줄 이내로 요약하세요.
- 민감 정보(개인정보)는 제외하세요.
- 결정 사항/요청 사항이 있으면 마지막 줄에 \"결론:\"으로 정리하세요.

[대화]
{chat_history}

[출력]
요약문만 출력하세요.
"""
)

SUMMARY_PROMPT = PromptTemplate(
    template=_SUMMARY_PROMPT,
    input_variables=["chat_history"],
)

# 서비스 요구사항에 맞게 규칙을 확장할 수 있다.
