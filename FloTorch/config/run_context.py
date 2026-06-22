from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RunContext:
    uid: str
    workspace_name: str
    email: str
    password: str
    # True when FloTorch/.env supplies at least one complete LLM provider credential set.
    has_detected_providers: bool
    first_provider: dict[str, Any] | None
    second_provider: dict[str, Any] | None
    selected_second_provider: dict[str, Any] | None
    embedding_provider: dict[str, Any] | None
    org_provider_name: str
    org_provider_description: str
    workspace_second_provider_name: str | None
    workspace_second_provider_description: str | None
    # Org provider selection (Bedrock > OpenAI > first .env provider)
    org_provider_type: str | None = None
    bedrock_configured: bool = False
    openai_configured: bool = False
    guardrail_tests_available: bool = False
    org_provider_skip_note: str = ""
    # Vector / RAG (at most one fallback vector CREATE; org reuse for Bedrock/OpenAI)
    vector_providers_planned: list[dict[str, Any]] = field(default_factory=list)
    vector_providers_skipped: list[str] = field(default_factory=list)
    org_verify_sections: list[str] = field(default_factory=list)
    vector_active_path: dict[str, Any] | None = None
    has_vector_providers_planned: bool = False
    has_vector_rag_path: bool = False
    # Optional model name override — when set, the agent selects this exact model instead of the first available.
    model_name: str = ""
    # Vector phase: whether a non-Bedrock/OpenAI org requires creating an OpenAI workspace provider
    # for embedding (set from vector_active_path by build_run_context).
    needs_openai_workspace_provider: bool = False
    # Evaluation filter — which eval experiments to run (llm, prompt, rag).
    # Empty list means "all". Set via FLOTORCH_EVAL_TYPES in .env (comma-separated).
    eval_types: list[str] = field(default_factory=list)
