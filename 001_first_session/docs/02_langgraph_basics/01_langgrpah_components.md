# 01. LangGraph 구성 요소: State, Node, Graph

## 이 챕터에서 다루는 내용

- LangGraph에서 **상태(State)**가 무엇인지
- **노드(Node)**가 하는 일과 입력/출력 규칙
- **그래프(Graph)**가 실행 흐름을 만드는 방식
- 초보자가 바로 이해할 수 있는 최소 예제

---

## 1. State: 노드들이 공유하는 데이터 박스

LangGraph의 핵심은 **상태(State)**입니다.
상태는 노드들이 주고받는 **공유 데이터 구조**이고, 그래프는 이 상태를 계속 갱신합니다.

- 상태는 **최소한의 필드**로 설계한다.
- 상태는 **사실 데이터**만 담고, 가공 결과는 새 키로 기록한다.
- 상태는 노드 간 계약(Contract)이다.

### 상태 예시

```python
from typing import TypedDict


class ReviewState(TypedDict):
    """리뷰 처리 흐름에서 공유되는 상태."""

    raw_text: str
    cleaned_text: str
    label: str
```

이 예시는 **입력(raw_text)** → **정제(cleaned_text)** → **라벨(label)** 흐름을 전제로 합니다.

### 커스텀 상태와 리듀서(Reducer)

실전에서는 **여러 노드가 같은 키를 업데이트**하는 경우가 있습니다.
이때는 **리듀서(Reducer)**로 병합 규칙을 명시하면 안전합니다.

- 리듀서는 **기존 값과 새 값**을 받아 **병합 결과**를 반환한다.
- 대표적인 예는 **로그 누적**, **메시지 히스토리 합치기**다.
- 리듀서를 쓰면 노드가 **부분 업데이트**만 반환해도 상태가 일관되게 합쳐진다.

#### 리듀서 예시 (리스트 누적)

```python
from typing import Annotated, TypedDict
import operator


class ReviewState(TypedDict):
    """리뷰 처리 흐름에서 공유되는 상태."""

    raw_text: str
    logs: Annotated[list[str], operator.add]
```

이 설정에서는 노드가 `{"logs": ["정제 완료"]}` 같은 **부분 업데이트**를 반환하면
기존 `logs`와 **자동으로 합쳐집니다**.

#### 커스텀 리듀서 예시 (최신 값 우선)

```python
from typing import Annotated, TypedDict


def keep_latest(old: str, new: str) -> str:
    """항상 최신 값을 유지하는 리듀서."""
    return new if new else old


class ReviewState(TypedDict):
    """리뷰 처리 흐름에서 공유되는 상태."""

    raw_text: str
    latest_label: Annotated[str, keep_latest]
```

리듀서는 **상태 키의 합의 규칙**이므로, 팀 내부에서 문서화해 두는 것이 좋습니다.

---

## 2. Node: 상태를 읽고, 상태를 갱신하는 함수

노드는 **상태를 입력받아 상태를 갱신하는 함수**입니다.
즉, 노드의 역할은 하나의 작은 작업을 수행하고, 결과를 상태에 기록하는 것입니다.

- 노드는 **한 가지 책임만** 가진다.
- 입력 상태를 직접 수정하지 않고, **새 상태를 반환**한다.
- 실패 가능성이 있는 경우, **오류 정보를 상태에 명시적으로 기록**한다.

### 노드의 최소 구조

```python
def clean_text(state: ReviewState) -> ReviewState:
    cleaned = state["raw_text"].strip()
    return {**state, "cleaned_text": cleaned}
```

### 전체 업데이트 vs. 부분 업데이트

노드는 보통 두 가지 방식으로 상태를 갱신합니다.

1. **전체 업데이트**: 상태 전체를 다시 만들어 반환한다.
2. **부분 업데이트**: 변경된 키만 반환한다(리듀서와 함께 쓰면 안전하다).

#### 전체 업데이트 예시

```python
def clean_text(state: ReviewState) -> ReviewState:
    cleaned = state["raw_text"].strip()
    return {**state, "cleaned_text": cleaned}
```

#### 부분 업데이트 예시 (리듀서 기반)

```python
def add_log(state: ReviewState) -> dict[str, list[str]]:
    return {"logs": ["clean: 정제 완료"]}
```

부분 업데이트는 **리듀서가 정의된 키**에서 특히 유용합니다.
리듀서가 없다면 전체 업데이트 방식이 더 안전합니다.

---

## 3. Graph: 노드들을 연결해 실행 흐름을 만든다

그래프는 노드들을 **엣지(Edge)**로 연결해 실행 순서를 정의합니다.

- `add_node`: 노드를 등록한다.
- `add_edge`: 노드 간 연결을 만든다.
- `set_entry_point`: 시작 노드를 지정한다.
- `END`: 실행 종료 지점을 의미한다.

즉, **그래프는 실행 순서의 설계도**입니다.

---

## 4. 가장 작은 예제 (State → Node → Graph)

아래 코드는 상태를 정의하고, 두 개의 노드를 연결한 **가장 단순한 파이프라인**입니다.
실제 LLM 호출은 `label` 노드 내부에 들어간다고 가정합니다.

```python
"""
목적: 상태/노드/그래프 관계를 가장 단순한 형태로 보여준다.
설명: 상태를 정의하고, 두 개의 노드를 연결해 파이프라인을 구성한다.
디자인 패턴: Pipeline
"""

from dataclasses import dataclass
from typing import TypedDict
from langgraph.graph import StateGraph, END


class ReviewState(TypedDict):
    """리뷰 처리 흐름에서 공유되는 상태."""

    raw_text: str
    cleaned_text: str
    label: str


@dataclass(frozen=True)
class ReviewPipelineBuilder:
    """리뷰 정제 → 라벨링 파이프라인 그래프를 생성하는 빌더."""

    def build(self) -> StateGraph:
        """파이프라인 그래프를 생성한다.

        Returns:
            StateGraph: 실행 가능한 그래프 객체.
        """
        graph = StateGraph(ReviewState)
        graph.add_node("clean", self._clean)
        graph.add_node("label", self._label)
        graph.add_edge("clean", "label")
        graph.add_edge("label", END)
        graph.set_entry_point("clean")
        return graph

    def _clean(self, state: ReviewState) -> ReviewState:
        """리뷰 텍스트를 정리한다."""
        cleaned = state["raw_text"].strip()
        return {**state, "cleaned_text": cleaned}

    def _label(self, state: ReviewState) -> ReviewState:
        """리뷰 라벨을 상태에 기록한다.

        실제 프로젝트에서는 이 위치에 LLM 호출이 들어간다.
        """
        label = "불만" if "불만" in state["cleaned_text"] else "일반"
        return {**state, "label": label}
```

### 사용 예 (개념)

```python
builder = ReviewPipelineBuilder()
graph = builder.build().compile()
result = graph.invoke({"raw_text": "불만이 있어서 문의드립니다."})
```

---

## 5. 초보자를 위한 설계 팁

- 상태 키는 **작고 명확한 이름**을 사용한다.
- 노드 출력은 **항상 상태 스키마를 만족**하도록 한다.
- 그래프는 먼저 **직선형 파이프라인**으로 시작하고, 익숙해지면 분기를 추가한다.

---

## 6. 구현 체크리스트

- 상태(State) 스키마가 문서화되어 있는가?
- 노드(Node)가 한 가지 책임만 수행하는가?
- 그래프(Graph)의 시작점과 종료점이 명확한가?
- 각 노드의 입력/출력 계약이 일관적인가?

---

## 7. Wrap-up: 상태/노드/그래프 + 리듀서를 한 번에 보기

아래 코드는 **상태 정의 + 리듀서 + 노드 + 그래프**를 하나로 묶은 예시입니다.
노드가 `logs`를 부분 업데이트하면, 리듀서가 자동으로 누적해 줍니다.

```python
"""
목적: 상태/노드/그래프/리듀서를 하나의 예제로 정리한다.
설명: 부분 업데이트와 리듀서 병합 규칙을 함께 보여준다.
디자인 패턴: Pipeline
"""

from dataclasses import dataclass
from typing import Annotated, TypedDict
import operator
from langgraph.graph import StateGraph, END


def keep_latest(old: str, new: str) -> str:
    """항상 최신 값을 유지하는 리듀서."""
    return new if new else old


class ReviewState(TypedDict):
    """리뷰 처리 흐름에서 공유되는 상태."""

    raw_text: str
    cleaned_text: str
    latest_label: Annotated[str, keep_latest]
    logs: Annotated[list[str], operator.add]


@dataclass(frozen=True)
class ReviewPipelineBuilder:
    """리뷰 정제 → 라벨링 파이프라인 그래프를 생성하는 빌더."""

    def build(self) -> StateGraph:
        """리듀서를 포함한 파이프라인 그래프를 생성한다."""
        graph = StateGraph(ReviewState)
        graph.add_node("clean", self._clean)
        graph.add_node("label", self._label)
        graph.add_edge("clean", "label")
        graph.add_edge("label", END)
        graph.set_entry_point("clean")
        return graph

    def _clean(self, state: ReviewState) -> ReviewState:
        """리뷰 텍스트를 정리하고 로그를 남긴다."""
        cleaned = state["raw_text"].strip()
        return {
            **state,
            "cleaned_text": cleaned,
            "logs": ["clean: 정제 완료"],
        }

    def _label(self, state: ReviewState) -> ReviewState:
        """라벨을 결정하고 로그를 남긴다."""
        label = "불만" if "불만" in state["cleaned_text"] else "일반"
        return {
            **state,
            "latest_label": label,
            "logs": [f"label: {label}"],
        }
```

### 사용 예 (개념)

```python
builder = ReviewPipelineBuilder()
graph = builder.build().compile()
result = graph.invoke({"raw_text": "불만이 있어서 문의드립니다.", "logs": []})
```
