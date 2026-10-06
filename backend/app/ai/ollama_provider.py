"""
Ollama-backed AI provider (local-first LLM runtime).

The model name is never hardcoded here: it comes from `settings.ollama_model`
(env var OLLAMA_MODEL), so operators can point this at any locally pulled
model (llama3.2, mistral, ...) without a code change.

This is a thin, isolated integration: ALL prompt construction and safety
framing lives in `app.ai.prompt` / `app.ai.document_prompts` (shared by every
provider), so this module only handles the Ollama HTTP calls and defensively
recovering a JSON object from the response. Downstream code still treats the
result as an unvalidated draft: it is parsed through a Pydantic schema before
anything is persisted, and the patient must review it.

Failure handling: every low-level `httpx` failure is translated into an
`AIGenerationError` with a short, patient/operator-safe message that says
what to do next (start Ollama, pull the model, wait for a cold start...).
The raw traceback is logged server-side only.
"""
from __future__ import annotations

import base64

import httpx

from app.ai.interface import AIProvider, AIStatus, AISummaryRequest, AISummaryResult
from app.ai.json_utils import extract_json_object
from app.ai.prompt import build_prompt
from app.core.config import settings
from app.core.exceptions import AIGenerationError
from app.core.logging import logger


class OllamaAIProvider(AIProvider):
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        vision_model: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model
        self.vision_model = vision_model or settings.ollama_vision_model
        # Injectable so tests can fake Ollama without a network.
        self._transport = transport

    # -- helpers --------------------------------------------------------
    def _client(self, timeout: float) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=timeout, transport=self._transport)

    async def _installed_models(self) -> list[str] | None:
        """Names of locally pulled models, or None if Ollama is unreachable."""
        try:
            async with self._client(3.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
            if resp.status_code != 200:
                return None
            return [m.get("name", "") for m in resp.json().get("models", [])]
        except (httpx.HTTPError, ValueError):
            return None

    @staticmethod
    def _model_is_installed(model: str, installed: list[str]) -> bool:
        wanted = model if ":" in model else f"{model}:latest"
        return any(name == wanted or name == model for name in installed)

    # -- availability ---------------------------------------------------
    async def is_available(self) -> bool:
        """True only if Ollama answers AND the configured model is actually
        pulled. (Checking reachability alone used to pass while every
        generation then failed with a 404 "model not found".)"""
        installed = await self._installed_models()
        return installed is not None and self._model_is_installed(self.model, installed)

    async def status(self) -> AIStatus:
        installed = await self._installed_models()
        if installed is None:
            return AIStatus(
                enabled=True,
                provider="ollama",
                available=False,
                model=self.model,
                model_ready=None,
                detail=(
                    f"Can't reach Ollama at {self.base_url}. Make sure Ollama is running "
                    "and, when the backend runs in Docker, that OLLAMA_HOST=0.0.0.0 is set "
                    "so the container can reach it."
                ),
            )
        ready = self._model_is_installed(self.model, installed)
        return AIStatus(
            enabled=True,
            provider="ollama",
            available=ready,
            model=self.model,
            model_ready=ready,
            detail=None
            if ready
            else f"Ollama is running but the model '{self.model}' isn't installed. "
            f"Run: ollama pull {self.model}",
        )

    # -- generation -----------------------------------------------------
    async def _generate(
        self, *, prompt: str, model: str, images: list[bytes] | None = None
    ) -> str:
        payload: dict = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            # Ollama's JSON mode: constrains output to valid JSON. Only a
            # best-effort hint -- callers validate against a Pydantic schema.
            "format": "json",
            "keep_alive": settings.ollama_keep_alive,
            "options": {
                "num_ctx": settings.ollama_num_ctx,
                "temperature": settings.ollama_temperature,
            },
        }
        if images:
            payload["images"] = [base64.b64encode(img).decode("ascii") for img in images]

        try:
            async with self._client(settings.ollama_timeout_seconds) as client:
                resp = await client.post(f"{self.base_url}/api/generate", json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.TimeoutException as exc:
            logger.warning(
                "Ollama timed out after %ss (model=%s).", settings.ollama_timeout_seconds, model
            )
            raise AIGenerationError(
                "The AI model took too long to respond. The first request after "
                "starting Ollama can be slow while the model loads - please try again."
            ) from exc
        except httpx.ConnectError as exc:
            logger.warning("Cannot connect to Ollama at %s.", self.base_url)
            raise AIGenerationError(
                "The AI service isn't reachable right now. Please try again later."
            ) from exc
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            logger.warning("Ollama returned HTTP %s (model=%s).", status_code, model)
            if status_code == 404:
                raise AIGenerationError(
                    f"The AI model '{model}' isn't installed on the AI server."
                ) from exc
            raise AIGenerationError(
                "The AI service returned an error. Please try again later."
            ) from exc
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Unexpected Ollama failure: %s", type(exc).__name__)
            raise AIGenerationError("The AI service failed. Please try again later.") from exc

        return (data.get("response") or "").strip()

    async def generate_summary(self, request: AISummaryRequest) -> AISummaryResult:
        raw_response = await self._generate(prompt=build_prompt(request), model=self.model)
        return AISummaryResult(
            summary_text=raw_response,
            structured_summary=extract_json_object(raw_response),
            model_name=self.model,
        )

    async def generate_json(
        self,
        *,
        prompt: str,
        images: list[bytes] | None = None,
        use_vision_model: bool = False,
    ) -> str:
        model = self.vision_model if use_vision_model else self.model
        return await self._generate(prompt=prompt, model=model, images=images)
