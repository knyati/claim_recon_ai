"""
ClaimRecon AI — LLM Provider Factory
Provider and model are fully configurable via .env — zero code changes needed
to switch between Gemini, OpenAI, and Anthropic.

.env variables:
    LLM_PROVIDER = gemini | openai | anthropic   (default: gemini)
    LLM_MODEL    = <model name>                  (default: gemini-2.0-flash)
"""
from __future__ import annotations


import os
from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel

load_dotenv()


def get_llm() -> BaseChatModel:
    """Return a LangChain chat model configured from environment variables."""
    provider = os.getenv("LLM_PROVIDER", "gemini").lower().strip()
    model = os.getenv("LLM_MODEL", "gemini-3.8-flash").strip()

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=0,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            request_timeout=25,          # 25s HTTP-level timeout
            max_retries=1,               # only 1 retry so we fail fast
        )

    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model,
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY"),
        )

    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model,
            temperature=0,
            api_key=os.getenv("ANTHROPIC_API_KEY"),
        )

    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER='{provider}'. "
            "Valid options: gemini | openai | anthropic"
        )
