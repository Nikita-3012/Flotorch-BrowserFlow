from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from FloTorch.config.execution_config import read_execution_config
from FloTorch.config.name_slug import name_field_slug, provider_name_with_uid
from FloTorch.config.run_context import RunContext
from FloTorch.config.vector_providers import (
    has_bedrock_llm_credentials,
    has_openai_llm_credentials,
    plan_vector_providers,
)

_VALID_EVAL_TYPES = ("llm", "prompt", "rag", "agent", "workflow")


def _parse_eval_types(raw) -> list[str]:
    """Parse EVAL_TYPES from execution.py or .env (list, comma-separated str, or 'all')."""
    if isinstance(raw, list):
        if not raw:
            return []
        return [t.strip().lower() for t in raw if str(t).strip().lower() in _VALID_EVAL_TYPES]
    if isinstance(raw, str):
        s = raw.strip().lower()
        if not s:
            return []
        if s == "all":
            return list(_VALID_EVAL_TYPES)
        return [t.strip() for t in s.split(",") if t.strip() in _VALID_EVAL_TYPES]
    return []


_FLOTORCH_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _FLOTORCH_ROOT / ".env"
load_dotenv(_ENV_FILE)
load_dotenv()

# Maps each credential env var to the provider display name (same string as in register()).
# Used to order detected providers by first occurrence of keys in FloTorch/.env.
# Per-provider base model env vars (first non-empty wins). FLOTORCH_MODEL_NAME overrides all.
_PROVIDER_MODEL_ENV_KEYS: dict[str, list[str]] = {
    "Groq": ["GROQ_MODEL"],
    "Google Generative AI": ["Google_MODEL", "GOOGLE_MODEL"],
    "Google Vertex AI": ["Google_VERTEX_MODEL", "GOOGLE_VERTEX_MODEL"],
    "OpenAI": ["OpenAI_MODEL", "OPENAI_MODEL"],
    "Amazon Bedrock": ["Amazon_MODEL", "AMAZON_MODEL", "AMAZON_BEDROCK_MODEL"],
    "Anthropic": ["Anthropic_MODEL", "ANTHROPIC_MODEL"],
    "DeepSeek": ["DeepSeek_MODEL", "DEEPSEEK_MODEL"],
    "Azure OpenAI": ["Azure_MODEL", "AZURE_OPENAI_MODEL"],
    "Cohere": ["Cohere_MODEL", "COHERE_MODEL"],
    "OpenAI Compatible": ["OpenAI_COMPATIBLE_MODEL"],
    "OpenRouter": ["OpenRouter_MODEL", "OPENROUTER_MODEL"],
}

_ENV_KEY_TO_PROVIDER_NAME: dict[str, str] = {
    "GROQ_API_KEY": "Groq",
    "GOOGLE_API_KEY": "Google Generative AI",
    "GOOGLE_VERTEX_PROJECT_ID": "Google Vertex AI",
    "GOOGLE_VERTEX_REGION": "Google Vertex AI",
    "GOOGLE_VERTEX_SERVICE_ACCOUNT": "Google Vertex AI",
    "GOOGLE_VERTEX_PRIVATE_KEY": "Google Vertex AI",
    "OPENAI_API_KEY": "OpenAI",
    "AMAZON_BEDROCK_ACCESS_KEY": "Amazon Bedrock",
    "AMAZON_BEDROCK_SECRET_KEY": "Amazon Bedrock",
    "AMAZON_BEDROCK_REGION": "Amazon Bedrock",
    "ANTHROPIC_API_KEY": "Anthropic",
    "DEEPSEEK_API_KEY": "DeepSeek",
    "AZURE_OPENAI_API_KEY": "Azure OpenAI",
    "AZURE_OPENAI_BASE_URL": "Azure OpenAI",
    "AZURE_OPENAI_API_VERSION": "Azure OpenAI",
    "COHERE_API_KEY": "Cohere",
    "OPENAI_COMPATIBLE_API_KEY": "OpenAI Compatible",
    "OPENAI_COMPATIBLE_BASE_URL": "OpenAI Compatible",
    "OPENROUTER_API_KEY": "OpenRouter",
    "OPENROUTER_BASE_URL": "OpenRouter",
}


def env(key: str) -> str:
    val = os.getenv(key, "")
    return val.strip() if val else ""


PROVIDERS: list[dict] = []
# Every integration type we know about (configured or not); filled by register().
ALL_PROVIDER_DEFINITIONS: list[dict] = []


def register(name: str, fields: dict, supports_embedding: bool = False) -> None:
    complete = all(v for v in fields.values())
    ALL_PROVIDER_DEFINITIONS.append(
        {
            "name": name,
            "supports_embedding": supports_embedding,
            "configured": complete,
        }
    )
    if complete:
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


def _prioritize_providers(providers: list[dict], preferred_name: str) -> list[dict]:
    """Move one detected provider to the front when FLOTORCH_PRIMARY_PROVIDER is set."""
    if not providers:
        return providers
    pref = preferred_name.strip()
    if not pref:
        return providers
    want = pref.lower()
    idx = next(
        (i for i, p in enumerate(providers) if p["name"].strip().lower() == want),
        None,
    )
    if idx is None:
        print(
            f'WARNING: FLOTORCH_PRIMARY_PROVIDER="{pref}" does not match any detected provider. '
            "Using default registration order (see providers.py register() sequence)."
        )
        return providers
    if idx == 0:
        return providers
    primary = providers[idx]
    rest = providers[:idx] + providers[idx + 1 :]
    return [primary] + rest


def _iter_assignment_keys_from_dotenv(path: Path):
    """Yield env var names in file order (simple KEY= parser; skips blank and # lines)."""
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, _ = line.partition("=")
        key = key.strip()
        if key:
            yield key


def _provider_names_order_from_env_file(env_path: Path) -> list[str]:
    """Order of provider types by first occurrence of any mapped credential key in the file."""
    seen: set[str] = set()
    order: list[str] = []
    for key in _iter_assignment_keys_from_dotenv(env_path):
        prov = _ENV_KEY_TO_PROVIDER_NAME.get(key)
        if prov and prov not in seen:
            seen.add(prov)
            order.append(prov)
    return order


def _order_providers_by_env_file(
    providers: list[dict], env_path: Path
) -> tuple[list[dict], bool]:
    """Reorder detected providers to match FloTorch/.env key order; fallback preserves registration order."""
    if not providers:
        return [], False
    file_order = _provider_names_order_from_env_file(env_path)
    if not file_order:
        return providers, False
    by_name = {p["name"]: p for p in providers}
    result: list[dict] = []
    for name in file_order:
        if name in by_name:
            result.append(by_name[name])
    placed = {p["name"] for p in result}
    for p in providers:
        if p["name"] not in placed:
            result.append(p)
    # True if we matched at least one detected provider to a line in the file
    matched_file = bool(result) and any(p["name"] in file_order for p in result)
    return (result if matched_file else providers), matched_file


def _order_providers_for_run(providers: list[dict]) -> tuple[list[dict], str]:
    """Resolve creation order: optional explicit primary, else FloTorch/.env line order, else registration order."""
    primary = env("FLOTORCH_PRIMARY_PROVIDER")
    if primary:
        ordered = _prioritize_providers(list(providers), primary)
        return ordered, "primary_override"
    ordered, used_env = _order_providers_by_env_file(list(providers), _ENV_FILE)
    if used_env:
        return ordered, "env_file"
    return ordered, "registration"


def print_provider_detection(
    run_order_providers: list[dict] | None = None, *, order_source: str = "registration"
) -> None:
    print("=" * 50)
    print("ALL PROVIDER TYPES (FloTorch supports)")
    print("=" * 50)
    for i, d in enumerate(ALL_PROVIDER_DEFINITIONS):
        emb = "embedding: YES" if d["supports_embedding"] else "embedding: NO"
        status = "CONFIGURED (complete keys in .env)" if d["configured"] else "not configured (missing keys)"
        print(f"  {i + 1}. {d['name']} — {emb} — {status}")
    print(f"\nTotal provider types: {len(ALL_PROVIDER_DEFINITIONS)}")
    print("=" * 50)
    print("DETECTED PROVIDERS (ready to use in this run)")
    print("=" * 50)
    detected = run_order_providers if run_order_providers is not None else PROVIDERS
    if not detected:
        print("  WARNING: No providers with complete credentials in .env.")
        print("  Provider creation (Steps 2, 5) and models (Steps 6–7) will be SKIPPED.")
        print("  Add the required keys for at least one provider under FloTorch/.env to enable them.")
        print("=" * 50)
        return
    primary_hint = env("FLOTORCH_PRIMARY_PROVIDER")
    if order_source == "primary_override" and primary_hint:
        print(
            f'  Order: #1 = organization provider — FLOTORCH_PRIMARY_PROVIDER="{primary_hint.strip()}" '
            "(overrides .env line order)."
        )
    elif order_source == "env_file":
        print(
            "  Order: #1 = organization provider — follows first occurrence of each provider’s "
            "credential keys in FloTorch/.env (top to bottom)."
        )
    else:
        print(
            "  Order: #1 = organization provider — providers.py register() sequence "
            "(no FloTorch/.env file order applied: missing file or no recognized provider keys in file)."
        )
    for i, p in enumerate(detected):
        emb = "embedding: YES" if p["supports_embedding"] else "embedding: NO"
        print(f"  {i + 1}. {p['name']} ({emb})")
    print(f"\nTotal ready for this run: {len(detected)}")
    print("=" * 50)


def _resolve_org_provider(ordered: list[dict]) -> tuple[dict | None, str]:
    """Priority chain: 1. Amazon Bedrock (if configured) → 2. OpenAI (if configured) → 3. First available provider."""
    if not ordered:
        print("  Org provider: None (no providers configured in .env)")
        return None, ""
    by_name = {p["name"]: p for p in ordered}
    if "Amazon Bedrock" in by_name:
        print("  Org provider: Amazon Bedrock (Bedrock credentials found — using as primary)")
        return by_name["Amazon Bedrock"], ""
    if "OpenAI" in by_name:
        print("  Org provider: OpenAI (Amazon Bedrock not configured — falling back to OpenAI)")
        return by_name["OpenAI"], ""
    fallback = ordered[0]
    print(
        f'  Org provider: {fallback["name"]} (no Bedrock or OpenAI configured — using first available)'
    )
    return fallback, ""


def resolve_run_model_name(
    *,
    explicit: str = "",
    org_provider: dict | None = None,
) -> str:
    """Base model for pipeline UI: FLOTORCH_MODEL_NAME, else org provider's *_MODEL in .env."""
    if explicit:
        return explicit
    if org_provider is None:
        return ""
    for key in _PROVIDER_MODEL_ENV_KEYS.get(org_provider["name"], []):
        val = env(key)
        if val:
            return val
    return ""


def _resolve_workspace_provider(
    ordered: list[dict], org: dict | None, *, env_override: str
) -> dict | None:
    if not ordered or org is None:
        return None
    if env_override:
        matched = next(
            (p for p in ordered if p["name"].strip().lower() == env_override.lower()),
            None,
        )
        if matched and matched["name"] != org["name"]:
            return matched
    for p in ordered:
        if p["name"] != org["name"]:
            return p
    return None


def build_run_context() -> RunContext:
    """Resolve credentials email/password, run id, and provider role assignments."""
    email = os.getenv("FLOTORCH_EMAIL")
    password = os.getenv("FLOTORCH_PASSWORD")
    uid = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    workspace_name = f"{name_field_slug('automation')}-{uid}"
    print(f"  Run id (uid): {uid}")
    print(f'  Workspace (create each run): "{workspace_name}"')

    ordered, order_source = _order_providers_for_run(PROVIDERS)
    print_provider_detection(ordered, order_source=order_source)

    has_detected_providers = bool(PROVIDERS)
    org_provider, _ = _resolve_org_provider(ordered)
    first_provider = org_provider
    second_provider = ordered[1] if len(ordered) > 1 else None

    bedrock_ok = has_bedrock_llm_credentials()
    openai_ok = has_openai_llm_credentials()
    org_skip_note = ""
    if not bedrock_ok:
        org_skip_note = (
            "Amazon Bedrock not configured in .env — cannot test Amazon Bedrock guardrail scenarios."
        )

    embedding_provider = (
        next((p for p in ordered if p["supports_embedding"]), None) if ordered else None
    )

    requested_provider_name = env("GOOGLE_PROVIDER_NAME") or env("PROVIDER_NAME")
    selected_second_provider = _resolve_workspace_provider(
        ordered, org_provider, env_override=requested_provider_name
    )
    if requested_provider_name and selected_second_provider is None and org_provider:
        print(
            f'WARNING: PROVIDER_NAME="{requested_provider_name}" not usable as workspace provider '
            "(same as org or missing). Using next available different provider."
        )
        selected_second_provider = _resolve_workspace_provider(ordered, org_provider, env_override="")

    org_provider_name = (
        provider_name_with_uid(org_provider["name"], uid) if org_provider else ""
    )
    org_provider_description = (
        f"{org_provider['name']} provider for automation-{uid}".lower()
        if org_provider
        else ""
    )
    workspace_second_provider_name = (
        provider_name_with_uid(selected_second_provider["name"], uid)
        if selected_second_provider
        else None
    )
    workspace_second_provider_description = (
        f"{selected_second_provider['name']} workspace provider for automation run {uid}".lower()
        if selected_second_provider
        else None
    )

    vector_planned, vector_skipped, org_verify_sections, vector_active_path = (
        plan_vector_providers(
            uid,
            org_provider_name=org_provider_name or None,
            org_provider_type=org_provider["name"] if org_provider else None,
        )
    )

    model_name = resolve_run_model_name(
        explicit=env("FLOTORCH_MODEL_NAME"),
        org_provider=org_provider,
    )
    if org_provider and model_name:
        print(
            f'  Base model for pipelines: "{model_name}" '
            f'(org provider "{org_provider["name"]}" — from FloTorch/.env).'
        )
    elif org_provider:
        print(
            f'  WARNING: No base model in .env for org provider "{org_provider["name"]}". '
            "Set FLOTORCH_MODEL_NAME or that provider's *_MODEL (e.g. GROQ_MODEL, Amazon_MODEL)."
        )

    _raw_eval_types = env("FLOTORCH_EVAL_TYPES")
    eval_types: list[str] = []

    # --- Try execution.py config first, fall back to .env FLOTORCH_EVAL_TYPES ---
    _exec_config = read_execution_config()
    if _exec_config is not None:
        _raw_eval_types = ""  # override .env — execution.py takes priority
        eval_types = _parse_eval_types(_exec_config.get("EVAL_TYPES", "all"))
        if eval_types:
            print(f'  Evaluations test case (execution.py): {", ".join(eval_types)}')
        else:
            print("  Evaluations test case: skipped (EVAL_TYPES empty — guardrails + prompt_partials only when MODULES=all)")

    if not _exec_config and _raw_eval_types and _raw_eval_types.strip().lower() != "all":
        eval_types = _parse_eval_types(_raw_eval_types)
    if eval_types and not _exec_config:
        print(f'  Eval filter active (.env): {", ".join(eval_types)}')

    return RunContext(
        uid=uid,
        workspace_name=workspace_name,
        email=email or "",
        password=password or "",
        has_detected_providers=has_detected_providers,
        first_provider=first_provider,
        second_provider=second_provider,
        selected_second_provider=selected_second_provider,
        embedding_provider=embedding_provider,
        org_provider_name=org_provider_name,
        org_provider_description=org_provider_description,
        workspace_second_provider_name=workspace_second_provider_name,
        workspace_second_provider_description=workspace_second_provider_description,
        org_provider_type=org_provider["name"] if org_provider else None,
        bedrock_configured=bedrock_ok,
        openai_configured=openai_ok,
        guardrail_tests_available=bedrock_ok,
        org_provider_skip_note=org_skip_note,
        vector_providers_planned=vector_planned,
        vector_providers_skipped=vector_skipped,
        org_verify_sections=org_verify_sections,
        vector_active_path=vector_active_path,
        has_vector_providers_planned=bool(vector_planned),
        has_vector_rag_path=vector_active_path is not None,
        model_name=model_name,
        needs_openai_workspace_provider=(
            vector_active_path is not None
            and vector_active_path.get("needs_openai_workspace_provider", False)
        ),
        eval_types=eval_types,
    )
