from __future__ import annotations

import asyncio

from google import genai


class GeminiError(RuntimeError):
    pass


class GeminiClient:
    def __init__(self, api_key: str | None, model: str, timeout_seconds: float):
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._client = genai.Client(api_key=api_key) if api_key else None

    @property
    def configured(self) -> bool:
        return self._client is not None

    async def generate(self, text: str) -> str:
        if self._client is None:
            raise GeminiError("Gemini is not configured")

        def request() -> str:
            assert self._client is not None
            response = self._client.models.generate_content(model=self.model, contents=text)
            if not response.text:
                raise GeminiError("Gemini returned an empty response")
            return response.text

        try:
            return await asyncio.wait_for(asyncio.to_thread(request), timeout=self.timeout_seconds)
        except TimeoutError as exc:
            raise GeminiError("Gemini request timed out") from exc
        except GeminiError:
            raise
        except Exception as exc:
            raise GeminiError("Gemini request failed") from exc

