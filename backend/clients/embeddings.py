from __future__ import annotations

from dataclasses import dataclass

from openai import OpenAI


class EmbeddingConfigurationError(RuntimeError):
    pass


class EmbeddingInvocationError(RuntimeError):
    pass


@dataclass(slots=True)
class OpenAIEmbeddingClient:
    api_key: str
    base_url: str
    model: str

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not self.api_key:
            raise EmbeddingConfigurationError("EMBEDDING_API_KEY is empty")
        if not self.model:
            raise EmbeddingConfigurationError("EMBEDDING_MODEL is empty")
        if not texts:
            return []

        try:
            client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            response = client.embeddings.create(model=self.model, input=texts)
        except Exception as exc:
            raise EmbeddingInvocationError(f"Embedding request failed: {exc}") from exc

        return [list(item.embedding) for item in sorted(response.data, key=lambda item: item.index)]

    def embed_query(self, text: str) -> list[float]:
        vectors = self.embed_documents([text])
        return vectors[0] if vectors else []


EmbeddingClient = OpenAIEmbeddingClient
