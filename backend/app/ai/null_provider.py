"""No-op AI provider used whenever AI_ENABLED=false. Lets the whole
application run without Ollama installed/configured, per project rule:
"the application must not require AI to boot or run."""
from app.ai.interface import AIProvider, AIStatus, AISummaryRequest, AISummaryResult


class NullAIProvider(AIProvider):
    async def generate_summary(self, request: AISummaryRequest) -> AISummaryResult:
        raise RuntimeError(
            "AI summary generation is disabled (AI_ENABLED=false or no provider configured)."
        )

    async def is_available(self) -> bool:
        return False

    async def generate_json(self, *, prompt, images=None, use_vision_model=False) -> str:
        raise RuntimeError("AI is disabled (AI_ENABLED=false or no provider configured).")

    async def status(self) -> AIStatus:
        return AIStatus(
            enabled=False,
            provider="none",
            available=False,
            detail="AI features are switched off for this deployment (AI_ENABLED=false).",
        )
