"""
Ollama-backed AI provider (local-first LLM runtime).

The model name is never hardcoded here: it comes from `settings.ollama_model`
(env var OLLAMA_MODEL), so operators can point this at any locally pulled
model (llama3.2, mistral, ...) without a code change.

This is a thin, isolated integration: ALL prompt construction and safety
framing lives in `app.ai.prompt` (shared by every provider), so this module
only handles the Ollama HTTP call and defensively recovering a JSON object
from its response. Downstream code (`AISummaryService`) still treats the
result as an unvalidated draft: it is parsed through
`app.ai.schemas.StructuredAISummary` before anything is persisted, and must
be reviewed by the patient before it can be shared with a doctor.
"""
import httpx

from app.ai.interface import AIProvider, AISummaryRequest, AISummaryResult
from app.ai.json_utils import extract_json_object
from app.ai.prompt import build_prompt
from app.core.config import settings


class OllamaAIProvider(AIProvider):
    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def generate_summary(self, request: AISummaryRequest) -> AISummaryResult:
        prompt = build_prompt(request)
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    # Ollama's JSON mode: asks the model to constrain its
                    # output to valid JSON. Still only a best-effort hint,
                    # not a guarantee -- `AISummaryService` validates the
                    # result against `StructuredAISummary` regardless and
                    # retries/rejects rather than trusting this alone.
                    "format": "json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        raw_response = (data.get("response") or "").strip()

        return AISummaryResult(
            summary_text=raw_response,
            structured_summary=extract_json_object(raw_response),
            model_name=self.model,
        )
