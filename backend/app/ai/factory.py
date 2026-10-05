from functools import lru_cache

from app.ai.interface import AIProvider
from app.ai.null_provider import NullAIProvider
from app.ai.ollama_provider import OllamaAIProvider
from app.core.config import settings


@lru_cache
def get_ai_provider() -> AIProvider:
    if not settings.ai_enabled:
        return NullAIProvider()
    if settings.ai_provider == "ollama":
        return OllamaAIProvider()
    return NullAIProvider()
