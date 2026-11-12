"""
ClaimRecon AI — LLM Provider Factory
Provider and model are fully configurable via .env — zero code changes needed
to switch between Gemini, OpenAI, Anthropic, and Azure OpenAI.

.env variables:
    LLM_PROVIDER = azure_openai | gemini | openai | anthropic   (default: gemini)
    LLM_MODEL    = <model or deployment name>                   (default: gemini-3.8-flash)
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

    if provider in ("azure_openai", "azure"):
        from langchain_openai import AzureChatOpenAI

        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", model)
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")

        if not endpoint:
            raise ValueError(
                "AZURE_OPENAI_ENDPOINT is required when LLM_PROVIDER='azure_openai'. "
                "Example: https://<my-resource>.openai.azure.com/"
            )

        if api_key:
            return AzureChatOpenAI(
                azure_endpoint=endpoint,
                azure_deployment=deployment,
                api_version=api_version,
                api_key=api_key,
                temperature=0,
                max_retries=2,
            )
        else:
            # Keyless Entra ID / Managed Identity authentication
            from azure.identity import DefaultAzureCredential, get_bearer_token_provider

            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(),
                "https://cognitiveservices.azure.com/.default",
            )
            return AzureChatOpenAI(
                azure_endpoint=endpoint,
                azure_deployment=deployment,
                api_version=api_version,
                azure_ad_token_provider=token_provider,
                temperature=0,
                max_retries=2,
            )

    elif provider == "gemini":
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
            "Valid options: azure_openai | gemini | openai | anthropic"
        )

