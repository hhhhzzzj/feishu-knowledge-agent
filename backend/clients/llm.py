from __future__ import annotations

from dataclasses import dataclass
import re

from openai import OpenAI


class LLMConfigurationError(RuntimeError):
    pass


class LLMInvocationError(RuntimeError):
    pass


@dataclass(slots=True)
class ChatCompletionResult:
    text: str
    model: str


@dataclass(slots=True)
class LLMChatClient:
    api_key: str
    base_url: str
    model: str

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> ChatCompletionResult:
        if not self.api_key:
            raise LLMConfigurationError("LLM_API_KEY is empty")
        if not self.model:
            raise LLMConfigurationError("LLM_MODEL is empty")

        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        try:
            response = client.chat.completions.create(
                model=self.model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception as exc:
            raise LLMInvocationError(f"LLM request failed: {exc}") from exc

        if not response.choices:
            raise LLMInvocationError("LLM response did not contain any choices")

        content = response.choices[0].message.content
        if not content:
            raise LLMInvocationError("LLM response did not contain message content")

        return ChatCompletionResult(text=_strip_think_blocks(content), model=response.model or self.model)


def _strip_think_blocks(text: str) -> str:
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    return cleaned.strip()
