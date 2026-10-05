"""No-op AI provider used whenever AI_ENABLED=false. Lets the whole
application run without Ollama installed/configured, per project rule:
"the application must not require AI to boot or run."""
from app.ai.interface import AIProvider, AISummaryRequest, AISummaryResult


class NullAIProvider(AIProvider):
    async def generate_summary(self, request: AISummaryRequest) -> AISummaryResult:
        raise RuntimeError(
            "AI summary generation is disabled (AI_ENABLED=false or no provider configured)."
        )

    async def is_available(self) -> bool:
        return False
