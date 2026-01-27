# 교육 내용 안내

이 문서는 LangChain/LangGraph 입문자를 위한 교재 모음입니다. 각 문서는 **설명 + 이유 + 예제 + 코드**를 포함하며, 실전 설계 관점에서 구성되었습니다.

## 교재 목록 (파일 링크)

### 01. 프롬프트 엔지니어링

- [01_프롬프트_기초와_원칙](./01_prompt_engineering/01_프롬프트_기초와_원칙.md)
- [02_프롬프트_구성_요소와_템플릿](./01_prompt_engineering/02_프롬프트_구성_요소와_템플릿.md)
- [03_프롬프트_개선_루프와_평가](./01_prompt_engineering/03_프롬프트_개선_루프와_평가.md)

### 02. LangGraph 기본 원칙

- [01_langgrpah_components](./02_langgraph_basics/01_langgrpah_components.md)
- [02_태스크_분리와_그래프_구조](./02_langgraph_basics/02_태스크_분리와_그래프_구조.md)
- [03_LLM_텍스트_도구_관점](./02_langgraph_basics/03_LLM_텍스트_도구_관점.md)
- [04_그래프_설계_패턴과_오류_처리](./02_langgraph_basics/04_그래프_설계_패턴과_오류_처리.md)

### 03. LLM 텍스트 처리

- [01_문자열_파이프라인_전략](./03_llm_text_handling/01_문자열_파이프라인_전략.md)
- [02_파싱_검증_정규화_실전](./03_llm_text_handling/02_파싱_검증_정규화_실전.md)

### 04. 문자열 트릭과 재시도 전략

- [01_yes_no_파서](./04_string_tricks/01_yes_no_파서.md)
- [02_single_choice_파서](./04_string_tricks/02_single_choice_파서.md)
- [03_multi_choice_파서](./04_string_tricks/03_multi_choice_파서.md)
- [04_json_안전_파싱](./04_string_tricks/04_json_안전_파싱.md)
- [05_retry_logic](./04_string_tricks/05_retry_logic.md)

## 사용 방법

1. `01_prompt_engineering`부터 순서대로 읽는다.
2. LangGraph 기본 원칙을 학습한 뒤 그래프 설계로 이동한다.
3. 문자열 파이프라인과 트릭 문서를 통해 출력 안정화 전략을 익힌다.
4. 재시도 전략을 실제 구현 흐름에 연결한다.

## 구현 체크리스트

- 프롬프트 출력 형식을 먼저 고정하고 파싱/검증 규칙을 함께 작성한다.
- 노드 간 상태(State) 필드를 최소화하고 명확히 정의한다.
- 실패 시 재시도/보수적 기본값/휴먼 리뷰 경로를 명확히 정한다.
- 샘플 코드를 프로젝트 규칙에 맞게 경량화하고 재사용 가능한 구조로 만든다.
