from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

from run_context import RunContext

load_dotenv()


def env(key: str) -> str:
    val = os.getenv(key, "")
    return val.strip() if val else ""


PROVIDERS: list[dict] = []


def register(name: str, fields: dict, supports_embedding: bool = False) -> None:
    if all(v for v in fields.values()):
        PROVIDERS.append(
            {
                "name": name,
                "fields": fields,
                "supports_embedding": supports_embedding,
            }
        )


register("Groq", {"API Key": env("GROQ_API_KEY")}, supports_embedding=False)
register(
    "Google Generative AI",
    {"API Key": env("GOOGLE_API_KEY")},
    supports_embedding=True,
)
register(
    "Google Vertex AI",
    {
        "Project ID": env("GOOGLE_VERTEX_PROJECT_ID"),
        "Region": env("GOOGLE_VERTEX_REGION"),
        "Service Account": env("GOOGLE_VERTEX_SERVICE_ACCOUNT"),
        "Private Key": env("GOOGLE_VERTEX_PRIVATE_KEY"),
    },
    supports_embedding=True,
)
register("OpenAI", {"API Key": env("OPENAI_API_KEY")}, supports_embedding=True)
register(
    "Amazon Bedrock",
    {
        "Access Key": env("AMAZON_BEDROCK_ACCESS_KEY"),
        "Secret Key": env("AMAZON_BEDROCK_SECRET_KEY"),
        "Region": env("AMAZON_BEDROCK_REGION"),
    },
    supports_embedding=True,
)
register("Anthropic", {"API Key": env("ANTHROPIC_API_KEY")}, supports_embedding=False)
register("DeepSeek", {"API Key": env("DEEPSEEK_API_KEY")}, supports_embedding=False)
register(
    "Azure OpenAI",
    {
        "API Key": env("AZURE_OPENAI_API_KEY"),
        "Base URL": env("AZURE_OPENAI_BASE_URL"),
        "API Version": env("AZURE_OPENAI_API_VERSION"),
    },
    supports_embedding=True,
)
register("Cohere", {"API Key": env("COHERE_API_KEY")}, supports_embedding=True)
register(
    "OpenAI Compatible",
    {
        "API Key": env("OPENAI_COMPATIBLE_API_KEY"),
        "Base URL": env("OPENAI_COMPATIBLE_BASE_URL"),
    },
    supports_embedding=False,
)
register(
    "OpenRouter",
    {
        "API Key": env("OPENROUTER_API_KEY"),
        "Base URL": env("OPENROUTER_BASE_URL"),
    },
    supports_embedding=False,
)


def fmt(provider: dict) -> str:
    lines = f"  Provider Type: {provider['name']}\n"
    for k, v in provider["fields"].items():
        lines += f"    {k}: {v}\n"
    return lines


def print_provider_detection() -> None:
    print("=" * 50)
    print("DETECTED PROVIDERS (from .env)")
    print("=" * 50)
    if not PROVIDERS:
        print("  ERROR: No providers with complete credentials!")
        sys.exit(1)
    for i, p in enumerate(PROVIDERS):
        emb = "embedding: YES" if p["supports_embedding"] else "embedding: NO"
        print(f"  {i + 1}. {p['name']} ({emb})")
    print(f"\nTotal: {len(PROVIDERS)} providers detected")
    print("=" * 50)


def build_run_context() -> RunContext:
    """Resolve credentials email/password, run id, and provider role assignments."""
    email = os.getenv("FLOTORCH_EMAIL")
    password = os.getenv("FLOTORCH_PASSWORD")
    uid = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    workspace_name = f"automation-{uid}"

    print_provider_detection()

    first_provider = PROVIDERS[0]
    second_provider = PROVIDERS[1] if len(PROVIDERS) > 1 else None
    embedding_provider = next((p for p in PROVIDERS if p["supports_embedding"]), None)

    requested_provider_name = env("GOOGLE_PROVIDER_NAME") or env("PROVIDER_NAME")
    selected_second_provider = second_provider
    if requested_provider_name:
        matched = next(
            (
                p
                for p in PROVIDERS
                if p["name"].strip().lower() == requested_provider_name.lower()
            ),
            None,
        )
        if matched:
            selected_second_provider = matched
        else:
            print(
                f'WARNING: PROVIDER_NAME="{requested_provider_name}" not found among detected providers. '
                "Falling back to default second provider."
            )

    org_provider_name = f"{first_provider['name']}-{uid}".lower()
    org_provider_description = f"{first_provider['name']} provider for automation".lower()
    workspace_second_provider_name = (
        f"{'-'.join(selected_second_provider['name'].lower().split())}-{uid}"
        if selected_second_provider
        else None
    )
    workspace_second_provider_description = (
        f"{selected_second_provider['name']} workspace provider for automation run {uid}".lower()
        if selected_second_provider
        else None
    )

    return RunContext(
        uid=uid,
        workspace_name=workspace_name,
        email=email or "",
        password=password or "",
        first_provider=first_provider,
        second_provider=second_provider,
        selected_second_provider=selected_second_provider,
        embedding_provider=embedding_provider,
        org_provider_name=org_provider_name,
        org_provider_description=org_provider_description,
        workspace_second_provider_name=workspace_second_provider_name,
        workspace_second_provider_description=workspace_second_provider_description,
    )
