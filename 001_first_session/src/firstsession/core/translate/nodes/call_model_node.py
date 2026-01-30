# 목적: 번역 모델 호출 노드를 정의한다.
# 설명: 실제 LLM/외부 번역 API 호출을 이 위치에서 수행한다.
# 디자인 패턴: 파이프라인 노드
# 참조: firstsession/core/translate/graphs/translate_graph.py

"""모델 호출 노드 모듈."""

import httpx
import logging


class CallModelNode:
    """모델 호출을 담당하는 노드."""

    _LOGGER = logging.getLogger(__name__)
    _OPENAI_API_KEY = ""
    _DEFAULT_MODEL = "gpt-4o-mini"
    _API_URL = "https://api.openai.com/v1/chat/completions"

    def run(self, prompt: str, model: str | None = None) -> str:
        """프롬프트를 기반으로 텍스트를 생성한다.

        Args:
            prompt: 모델에 전달할 프롬프트.
            model: 사용할 모델 이름(없으면 기본값 사용).

        Returns:
            str: 모델 응답 텍스트.
        """
        if not prompt:
            self._LOGGER.error("모델 호출 실패: 프롬프트가 비어 있습니다.")
            return ""

        if not self._OPENAI_API_KEY:
            self._LOGGER.error("모델 호출 실패: OPENAI_API_KEY가 설정되지 않았습니다.")
            return ""

        try:
            content = self._call_openai(
                prompt=prompt,
                model=model or self._DEFAULT_MODEL,
            )
        except httpx.HTTPError as exc:
            self._LOGGER.exception("모델 호출 실패: %s", exc)
            return ""

        return content

    def _call_openai(self, prompt: str, model: str) -> str:
        """OpenAI Chat Completions API로 텍스트를 생성한다."""
        headers = {
            "Authorization": f"Bearer {self._OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }
        with httpx.Client(timeout=30.0) as client:
            response = client.post(self._API_URL, headers=headers, json=payload)
            response.raise_for_status()

        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            return ""
        message = choices[0].get("message", {})
        return (message.get("content") or "").strip()
