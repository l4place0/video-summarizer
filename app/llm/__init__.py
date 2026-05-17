from app.llm.base import BaseLLM
from app.llm.claude import ClaudeLLM
from app.llm.openai_proto import OpenAILLM

_PROVIDERS = {
    "claude": ClaudeLLM,
    "openai": OpenAILLM,
}


def get_llm(provider: str | None = None) -> BaseLLM:
    from app.core.config import settings

    provider = provider or settings.llm_provider
    cls = _PROVIDERS.get(provider)
    if not cls:
        raise ValueError(f"Unknown LLM provider: {provider}. Available: {list(_PROVIDERS.keys())}")
    return cls()
