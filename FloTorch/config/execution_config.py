"""Single source for FloTorch/execution.py settings."""

from __future__ import annotations

from typing import Any


def read_execution_config() -> dict[str, Any] | None:
    """Return execution plan dict, or None if execution.py is unavailable."""
    try:
        from FloTorch import execution as exec_cfg  # type: ignore[import-untyped]

        return {
            "EVAL_TYPES": getattr(exec_cfg, "EVAL_TYPES", "all"),
            "MODULES": getattr(exec_cfg, "MODULES", "all"),
            "SKIP_ORG_PROVIDER": bool(getattr(exec_cfg, "SKIP_ORG_PROVIDER", False)),
        }
    except Exception:
        return None


def execution_modules_raw() -> Any | None:
    """MODULES value from execution.py, or None when not using execution plan."""
    cfg = read_execution_config()
    if cfg is None:
        return None
    return cfg.get("MODULES", "all")


_WORKFLOW_ALIASES: dict[str, str] = {
    "guardrail": "guardrails",
    "partial": "prompt_partials",
    "partials": "prompt_partials",
    "evaluation": "evaluations",
    "workflow": "workflow_evaluation",
}

_VALID_WORKFLOW_MODES = frozenset(
    {"full", "guardrails", "prompt_partials", "evaluations", "workflow_evaluation"}
)


def derive_workflow_mode_from_modules(
    modules: Any,
    *,
    eval_types: list[str] | None = None,
) -> str:
    """Map execution.py MODULES to FLOTORCH_WORKFLOW-style mode (reporting / banners)."""
    if modules is None:
        return "full"
    if isinstance(modules, str):
        raw = modules.strip().lower()
        if raw == "all":
            return "full"
        if raw in _WORKFLOW_ALIASES:
            return _WORKFLOW_ALIASES[raw]
        if raw in _VALID_WORKFLOW_MODES:
            return raw
        parts = [p.strip().lower() for p in raw.split(",") if p.strip()]
    elif isinstance(modules, list):
        parts = [str(m).strip().lower() for m in modules if str(m).strip()]
    else:
        return "full"

    if not parts:
        return "full"
    if len(parts) == 1:
        return derive_workflow_mode_from_modules(parts[0], eval_types=eval_types)

    test_cases = frozenset({"guardrails", "prompt_partials", "partials", "evaluations"})
    if all(p in test_cases for p in parts):
        if parts == ["guardrails"]:
            return "guardrails"
        if set(parts) <= {"prompt_partials", "partials"}:
            return "prompt_partials"
        if "evaluations" in parts or eval_types:
            return "evaluations"
    return "full"
