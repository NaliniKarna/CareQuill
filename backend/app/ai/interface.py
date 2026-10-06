"""
AI provider abstraction.

IMPORTANT SAFETY CONTRACT: any implementation of `AIProvider.generate_summary`
must only organize/summarize the structured, patient-verified data it is
given. It must never diagnose, prescribe, suggest medication changes, claim
certainty about conditions, or fabricate history. Prompt construction that
enforces this lives alongside each provider implementation and is covered by
tests before this is wired into an API route.

This interface is intentionally provider-agnostic: `app.services` code
should depend on `AIProvider`, never on Ollama or any specific SDK, so the
provider (and even the model name) can change via configuration alone.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class AISummaryRequest:
    patient_id: str
    snapshot_data: dict
    prompt_version: str
    # Optional context beyond the verified snapshot -- see
    # `app.ai.prompt.build_prompt` for exactly how each is framed for the
    # model (the safety-critical part: document_extractions must always be
    # labeled AI-extracted/unverified, never merged into verified data).
    patient_concerns: str | None = None
    document_extractions: list[dict] = field(default_factory=list)
    timeline_entries: list[dict] = field(default_factory=list)
    # Set by `AISummaryService` for the single safe retry after the first
    # response failed to validate as `StructuredAISummary` -- providers use
    # this to append a stricter "reply with ONLY valid JSON" instruction.
    strict_json_retry: bool = False


@dataclass
class AISummaryResult:
    summary_text: str
    structured_summary: dict | None
    model_name: str


@dataclass
class AIStatus:
    """Operator/patient-facing diagnostics: why AI features do or don't work.
    `detail` is always safe to show in the UI (never a stack trace)."""

    enabled: bool
    provider: str
    available: bool
    model: str | None = None
    model_ready: bool | None = None
    detail: str | None = None


class AIProvider(ABC):
    @abstractmethod
    async def generate_summary(self, request: AISummaryRequest) -> AISummaryResult:
        ...

    async def generate_json(
        self,
        *,
        prompt: str,
        images: list[bytes] | None = None,
        use_vision_model: bool = False,
    ) -> str:
        """Generic "prompt in, raw JSON text out" call used by the document
        features (entity extraction, plain-language explanation, image
        description). Callers are responsible for building a safe prompt
        (see `app.ai.document_prompts`) and for validating the returned text
        with a Pydantic schema -- exactly like the summary flow, nothing a
        provider returns is trusted as-is.

        Not abstract so existing providers/test doubles that only implement
        summaries keep working; the default simply reports "unsupported"."""
        raise NotImplementedError("This AI provider does not support generic JSON generation.")

    async def status(self) -> AIStatus:
        return AIStatus(
            enabled=True,
            provider=type(self).__name__,
            available=await self.is_available(),
        )

    @abstractmethod
    async def is_available(self) -> bool:
        """Whether the provider is currently reachable/configured. Used so
        the rest of the app can degrade gracefully (AI_ENABLED=false or the
        provider being unreachable must never prevent the app from running)."""
