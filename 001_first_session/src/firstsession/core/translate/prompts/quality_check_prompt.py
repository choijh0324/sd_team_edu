# 목적: 번역 품질 검사 프롬프트 템플릿을 제공한다.
# 설명: 원문과 번역문을 비교해 YES/NO로 통과 여부를 판단한다.
# 디자인 패턴: Singleton
# 참조: docs/04_string_tricks/01_yes_no_파서.md

"""번역 품질 검사 프롬프트 템플릿 모듈."""

from textwrap import dedent
from langchain_core.prompts import PromptTemplate

_QUALITY_CHECK_PROMPT = dedent(
    """\
You are a translation quality reviewer.

[Evaluation Criteria]
1. Accuracy: Is the source meaning conveyed correctly without omissions or distortion?
2. Fluency: Does the translation sound natural to target-language speakers?
3. Style & Tone: Is the original mood, intent, and tone preserved?
4. Context Awareness: Is the meaning preserved with full context, not just sentence-level?
5. Terminology Consistency: Are terms and concepts translated consistently?
6. Cultural Appropriateness: Is it culturally appropriate and free of potential misunderstandings?
7. Readability & Flow: Is the translation easy to read and well-paced?
8. Functional Adequacy: Is the translation fit for its intended use?

[Rules]
- Output must be exactly one word: YES or NO.
- No explanation, whitespace, punctuation, or quotes.

[Source]
{source_text}

[Translation]
{translated_text}

[Output]
YES or NO
"""
)

QUALITY_CHECK_PROMPT = PromptTemplate(
    template=_QUALITY_CHECK_PROMPT,
    input_variables=["source_text", "translated_text"],
)
