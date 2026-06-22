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
