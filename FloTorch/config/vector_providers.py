"""Vector storage provider detection from FloTorch/.env and repository defaults."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from FloTorch.config.name_slug import name_field_slug, provider_name_with_uid

_FLOTORCH_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_FLOTORCH_ROOT / ".env")
load_dotenv()


def env(key: str) -> str:
    val = os.getenv(key, "")
    return val.strip() if val else ""


VECTOR_PROVIDERS: list[dict[str, Any]] = []


def _register_vector(
    display_name: str,
    fields: dict[str, str],
    *,
    internal_key: str | None = None,
) -> None:
    key = internal_key or name_field_slug(display_name)
    complete = all(v for v in fields.values())
    entry: dict[str, Any] = {
        "name": display_name,
        "key": key,
        "fields": fields,
        "configured": complete,
    }
    if complete:
        VECTOR_PROVIDERS.append(entry)


_register_vector(
    "Pinecone",
    {"API Key": env("PINECONE_API_KEY"), "Base URL": env("PINECONE_BASE_URL")},
)
_register_vector(
    "Chroma",
    {
        "API Key": env("CHROMA_API_KEY"),
        "Tenant": env("CHROMA_TENANT"),
        "Database": env("CHROMA_DATABASE"),
    },
)
_register_vector(
    "LanceDB",
    {"API Key": env("LANCEDB_API_KEY"), "URI": env("LANCEDB_URI")},
)
_register_vector(
    "pg-vector",
    {
        "Host": env("PG_VECTOR_HOST"),
        "Port": env("PG_VECTOR_PORT"),
        "Database": env("PG_VECTOR_DATABASE"),
        "User": env("PG_VECTOR_USER"),
        "Password": env("PG_VECTOR_PASSWORD"),
    },
    internal_key="pgvector",
)
_register_vector(
    "Azure AI Search",
    {
        "API Key": env("AZURE_AI_SEARCH_API_KEY"),
        "Base URL": env("AZURE_AI_SEARCH_BASE_URL"),
        "API Version": env("AZURE_AI_SEARCH_API_VERSION"),
    },
    internal_key="azure_ai_search",
)
_register_vector(
    "OpenAI",
    {"API Key": env("OPENAI_API_KEY")},
    internal_key="openai_vector",
)
_register_vector(
    "Amazon Bedrock",
    {
        "Access Key": env("AMAZON_BEDROCK_ACCESS_KEY"),
        "Secret Key": env("AMAZON_BEDROCK_SECRET_KEY"),
        "Region": env("AMAZON_BEDROCK_REGION"),
    },
    internal_key="amazon_bedrock_vector",
)

REPOSITORY_DEFAULTS: dict[str, dict[str, str]] = {
    "pinecone": {
        "table_name": env("PINECONE_TABLE_NAME") or "amazon-bedrock-full-dataset",
        "embedding_model": env("PINECONE_EMBEDDING_MODEL") or "openai-small",
        "table_is_dropdown": "true",
    },
    "chroma": {
        "table_name": env("CHROMA_TABLE_NAME") or "anthropic_dataset",
        "embedding_model": env("CHROMA_EMBEDDING_MODEL") or env("Chroma_EMBEDDING_MODEL") or "openai-small",
        "table_is_dropdown": "true",
    },
    "azure_ai_search": {
        "table_name": "azure-vector-index50d",
        "embedding_model": "",
        "table_is_dropdown": "true",
    },
    "lancedb": {
        "table_name": env("LANCEDB_TABLE_NAME") or "Amazon-Bedrock-100pages-Dataset",
        "embedding_model": env("LANCEDB_EMBEDDING_MODEL") or "openai-small",
        "table_is_dropdown": "true",
    },
    "openai_vector": {
        "table_name": "anthropic",
        "embedding_model": "",
        "table_is_dropdown": "true",
    },
    "amazon_bedrock_vector": {
        "table_name": "anthropic-dataset",
        "embedding_model": "",
        "table_is_dropdown": "true",
    },
    "pgvector": {
        "table_name": env("PG_VECTOR_TABLE_NAME") or "anthropic_dataset",
        "embedding_model": env("PG_VECTOR_EMBEDDING_MODEL") or "openai-small",
        "table_is_dropdown": "false",
    },
}

RAG_DATASET_FILE: dict[str, str] = {
    "chroma": "anthropic-3qa-dataset.json",
    "amazon_bedrock_vector": "anthropic-3qa-dataset.json",
    "pgvector": "anthropic-3qa-dataset.json",
    "azure_ai_search": "anthropic-3qa-dataset.json",
    "openai_vector": "anthropic-3qa-dataset.json",
    "lancedb": "3qa.json",
    "pinecone": "3qa.json",
}


def has_openai_llm_credentials() -> bool:
    return bool(env("OPENAI_API_KEY"))


def has_bedrock_llm_credentials() -> bool:
    return all(
        env(k)
        for k in (
            "AMAZON_BEDROCK_ACCESS_KEY",
            "AMAZON_BEDROCK_SECRET_KEY",
            "AMAZON_BEDROCK_REGION",
        )
    )


def first_configured_vector_provider() -> dict[str, Any] | None:
    """First vector DB in registration order with complete .env credentials."""
    return next((vp for vp in VECTOR_PROVIDERS if vp.get("configured")), None)


def org_verify_sections_for_type(org_provider_type: str | None) -> list[str]:
    if org_provider_type == "Amazon Bedrock":
        return ["Model Provider", "Vector storage provider", "Guardrails provider"]
    if org_provider_type == "OpenAI":
        return ["Model Provider", "Vector storage provider"]
    return []


def _vector_job_from_provider(vp: dict[str, Any], uid: str) -> dict[str, Any]:
    key = vp["key"]
    return {
        **vp,
        "provider_instance_name": provider_name_with_uid(vp["name"], uid),
        "repository": REPOSITORY_DEFAULTS.get(key, {}),
        "rag_dataset_file": RAG_DATASET_FILE.get(key, "anthropic-3qa-dataset.json"),
        "rag_dataset_name": f"rag-{name_field_slug(vp['name'])}-{uid}",
        "repository_name": f"repo-{name_field_slug(vp['name'])}-{uid}",
        "rag_eval_name": f"rag-evals-{name_field_slug(vp['name'])}-{uid}",
    }


def _org_vector_key(org_provider_type: str | None) -> str:
    """Map org provider type to its vector key for REPOSITORY_DEFAULTS / RAG_DATASET_FILE lookup."""
    if org_provider_type == "Amazon Bedrock":
        return "amazon_bedrock_vector"
    if org_provider_type == "OpenAI":
        return "openai_vector"
    return ""


def _openai_embedding_model_for_vector_key(key: str) -> str:
    """Embedding model name to create when a non-Azure vector DB needs OpenAI."""
    return "text-embedding-ada-002" if key == "lancedb" else "text-embedding-3-small"


def _vector_needs_openai_embedding(key: str) -> bool:
    """Pinecone, Chroma, LanceDB, pg-vector need OpenAI for embedding; Azure does not."""
    return key != "azure_ai_search"


def plan_vector_providers(
    uid: str,
    *,
    org_provider_name: str | None,
    org_provider_type: str | None,
) -> tuple[list[dict[str, Any]], list[str], list[str], dict[str, Any] | None]:
    """
    Returns:
      - vector_providers_planned: 0 or 1 optional CREATE job (fallback vector only)
      - skip notes
      - org_verify_sections: UI section names to search org provider in (Bedrock/OpenAI org only)
      - vector_active_path: single RAG chain descriptor (org reuse or one vector)
    """
    skipped: list[str] = []
    planned: list[dict[str, Any]] = []
    verify_sections = org_verify_sections_for_type(org_provider_type)
    fallback = first_configured_vector_provider()

    # ── Case A / B: Org is Amazon Bedrock or OpenAI (try to reuse at workspace level) ──
    if verify_sections and org_provider_name:
        org_key = _org_vector_key(org_provider_type)
        active: dict[str, Any] = {
            "provider_ref": org_provider_name,
            "org_provider_name": org_provider_name,
            "org_provider_type": org_provider_type,
            "verify_sections": verify_sections,
            "use_org_provider": True,
            "repository": REPOSITORY_DEFAULTS.get(org_key, {}),
            "repository_name": f"repo-{org_key}-{uid}",
            "rag_dataset_file": RAG_DATASET_FILE.get(org_key, "anthropic-3qa-dataset.json"),
            "rag_dataset_name": f"rag-{name_field_slug(org_key)}-{uid}",
            "rag_eval_name": f"rag-evals-{name_field_slug(org_key)}-{uid}",
        }
        if fallback:
            job = _vector_job_from_provider(fallback, uid)
            job["create_only_if_org_missing_in_vector_section"] = True
            planned.append(job)
            active["fallback_job"] = job
        else:
            skipped.append(
                "No vector DB credentials in .env — if org provider is missing from Vector "
                "storage section, nothing to create."
            )
        if org_provider_type == "OpenAI" and not has_openai_llm_credentials():
            skipped.append("OpenAI org provider but OPENAI_API_KEY missing in .env.")
        return planned, skipped, verify_sections, active

    # ── Case C / D: Org is NOT Bedrock/OpenAI — create first available vector from .env ──
    if fallback:
        job = _vector_job_from_provider(fallback, uid)
        planned.append(job)
        v_key = fallback["key"]
        active: dict[str, Any] = {
            "provider_ref": job["provider_instance_name"],
            "use_org_provider": False,
            **job,
        }

        if _vector_needs_openai_embedding(v_key):
            active["needs_openai_embedding"] = True
            repo_emb = (job.get("repository") or {}).get("embedding_model", "")
            active["openai_embedding_model"] = (
                repo_emb or _openai_embedding_model_for_vector_key(v_key)
            )

            if has_openai_llm_credentials():
                ws_openai_name = f"openai-{uid}"
                active["needs_openai_workspace_provider"] = True
                active["openai_workspace_provider_name"] = ws_openai_name
                active["openai_workspace_provider_desc"] = (
                    f"openai workspace provider for automation run {uid}".lower()
                )
            else:
                skipped.append(
                    "Cannot test vector storage — OpenAI credentials not in .env "
                    "(required for embedding with Pinecone/Chroma/LanceDB/pg-vector)."
                )

        return planned, skipped, [], active

    skipped.append("SKIP vector/RAG — no vector database credentials in FloTorch/.env.")
    return [], skipped, [], None


def dataset_path_for_vector(job: dict[str, Any]) -> str:
    root = _FLOTORCH_ROOT / "Dataset"
    return str((root / job["rag_dataset_file"]).resolve())
