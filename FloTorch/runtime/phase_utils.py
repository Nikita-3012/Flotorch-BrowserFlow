"""Helpers for multi-phase browser-use runs."""

from __future__ import annotations

from browser_use.agent.views import AgentHistoryList


def _text_blobs_from_history(history: AgentHistoryList | None) -> str:
    if history is None:
        return ""
    parts: list[str] = []
    fr = history.final_result()
    if fr:
        parts.append(str(fr))
    if not history.history:
        return "\n".join(parts)
    for h in history.history:
        mo = h.model_output
        if not mo:
            continue
        for attr in ("memory", "next_goal", "evaluation_previous_goal", "thinking"):
            val = getattr(mo, attr, None)
            if val:
                parts.append(str(val))
    return "\n".join(parts)


def history_mentions_token(history: AgentHistoryList | None, token: str) -> bool:
    if not token or history is None:
        return False
    return token in _text_blobs_from_history(history)
