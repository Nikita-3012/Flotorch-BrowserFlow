"""Summarize pass/fail for TC-01 login and the post-login workflow (Steps 2–10)."""

from __future__ import annotations

import html
import json
import re
from typing import Any

from browser_use.agent.views import AgentHistoryList, AgentOutput


def _verdict_token(history: AgentHistoryList | None) -> tuple[str, str]:
    """Return (PASS|FAIL|INCOMPLETE|N/A, short reason)."""
    if history is None:
        return "N/A", "not executed"

    if not history.is_done():
        return "INCOMPLETE", "agent did not finish with a terminal done action"

    success = history.is_successful()
    if success is True:
        return "PASS", "done with success=true"
    if success is False:
        return "FAIL", "done with success=false"
    return "INCOMPLETE", "done but success flag missing"


def _collect_step_errors(history: AgentHistoryList | None) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    if history is None:
        return out
    for i, err in enumerate(history.errors()):
        if err:
            out.append((i, str(err)))
    return out


def _parse_final_summary_lines(final_text: str | None) -> list[tuple[str, str]]:
    """
    Best-effort parse of FINAL SUMMARY bullets (numbered lines).
    Returns (line excerpt, guessed status).
    """
    if not final_text or not final_text.strip():
        return []

    status_words = re.compile(
        r"\b(PASS|PASSED|FAIL|FAILED|SKIP|SKIPPED|ERROR|COMPLETE|COMPLETED|OK|SUCCESS|SUCCEEDED)\b",
        re.IGNORECASE,
    )
    rows: list[tuple[str, str]] = []
    for raw_line in final_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if not re.match(r"^\d+\.", line):
            continue

        tail = line
        if "—" in line:
            tail = line.rsplit("—", 1)[-1].strip()
        elif re.match(r".*\s[-–]\s", line):
            tail = line.rsplit("-", 1)[-1].strip()

        m = status_words.search(tail)
        if not m:
            rows.append((line[:120] + ("..." if len(line) > 120 else ""), "UNKNOWN"))
            continue

        w = m.group(1).upper()
        if w in ("PASS", "PASSED", "COMPLETE", "COMPLETED", "OK", "SUCCESS", "SUCCEEDED"):
            status = "PASS"
        elif w in ("FAIL", "FAILED", "ERROR"):
            status = "FAIL"
        elif w in ("SKIP", "SKIPPED"):
            status = "SKIP"
        else:
            status = "UNKNOWN"

        excerpt = line[:120] + ("..." if len(line) > 120 else "")
        rows.append((excerpt, status))

    return rows


def _collapse_ws(text: str | None) -> str:
    if not text:
        return ""
    return " ".join(str(text).split())


def _snip(text: str | None, max_len: int) -> str:
    t = _collapse_ws(text)
    if len(t) <= max_len:
        return t
    return t[: max_len - 3] + "..."


def _action_type_names(mo: AgentOutput) -> str:
    if not mo.action:
        return "(no actions)"
    names: list[str] = []
    for act in mo.action:
        data = act.model_dump(exclude_none=True, mode="json")
        for key in data:
            if key == "interacted_element":
                continue
            names.append(key)
            break
    return ", ".join(names) if names else "(unknown)"


def _short_url(url: str, max_len: int = 52) -> str:
    u = url.strip() or "(no url)"
    if len(u) <= max_len:
        return u
    return "…" + u[-(max_len - 1) :]


def _humanize_tool_line(text: str) -> str:
    """Short, mail-friendly description; avoids echoing secrets from Typed lines."""
    t = _collapse_ws(text)
    if not t:
        return ""
    low = t.lower()
    if "navigated to" in low or t.startswith("🔗") or ("navigated" in low and "http" in low):
        murl = re.search(r"(https?://[^\s]+)", t)
        if murl:
            return f"navigate → {_short_url(murl.group(1), 44)}"
        return "navigate"
    if low.startswith("typed"):
        if "@" in t:
            return "typed email"
        return "typed password"
    if "clicked" in low:
        m = re.search(r'"([^"]{1,36})"', t)
        if m:
            return f"click «{_snip(m.group(1), 32)}»"
        return "click"
    if "task completed" in low or "login failed" in low or "test case" in low:
        return _snip(t, 140)
    return _snip(t, 120)


def _outcome_compact_line(h: Any, *, max_total: int = 240) -> str:
    segs: list[str] = []
    for r in getattr(h, "result", []) or []:
        if getattr(r, "error", None):
            segs.append(f"error: {_snip(str(r.error), 70)}")
            continue
        ec = getattr(r, "extracted_content", None)
        lt = getattr(r, "long_term_memory", None)
        chunk = ec or lt
        if chunk:
            segs.append(_humanize_tool_line(str(chunk)))
        if getattr(r, "is_done", False):
            succ = r.success
            segs.append(f"done({succ})")
    line = " → ".join(s for s in segs if s)
    if not line:
        return "—"
    return _snip(line, max_total)


# ---------------------------------------------------------------------------
# Plain-text Unicode-box table rendering
# ---------------------------------------------------------------------------

# Plain-text labels for the Result column (no emoji — keeps column widths predictable
# across consoles that render emoji as 1- or 2-cells inconsistently).
def _verdict_label_plain(eval_text: str | None) -> str:
    label, _color, _emoji = _verdict_from_eval(eval_text)
    return label


def _step_what_text(h: Any) -> str:
    """Natural-language description used in the 'What the Agent Did' table cell.

    Line 1: agent's `evaluation_previous_goal` with any trailing `Verdict: ...` stripped.
    Line 2: short action/outcome summary (navigate URL / click target / typed email / done).
    """
    mo = h.model_output
    eval_clean = ""
    if mo:
        eval_clean = _step_eval_clean(mo.evaluation_previous_goal or "")
    outcome = _outcome_compact_line(h, max_total=200)

    if eval_clean and outcome and outcome != "—":
        return f"{eval_clean}\n{outcome}"
    if eval_clean:
        return eval_clean
    if outcome and outcome != "—":
        return outcome
    return "(no detail)"


def _wrap_cell(text: str, width: int) -> list[str]:
    """Word-wrap text into lines no wider than `width`, preserving embedded newlines."""
    if width <= 0:
        return [""]
    if not text:
        return [""]
    out: list[str] = []
    for paragraph in str(text).split("\n"):
        if not paragraph:
            out.append("")
            continue
        words = paragraph.split(" ")
        cur = ""
        for w in words:
            cand = w if not cur else cur + " " + w
            if len(cand) <= width:
                cur = cand
                continue
            if cur:
                out.append(cur)
            while len(w) > width:
                out.append(w[:width])
                w = w[width:]
            cur = w
        if cur:
            out.append(cur)
    return out or [""]


def _pad_cell(s: str, width: int, alignment: str = "left") -> str:
    if width <= 0:
        return ""
    if len(s) > width:
        s = (s[: width - 1] + "…") if width > 1 else s[:width]
    if alignment == "center":
        return s.center(width)
    if alignment == "right":
        return s.rjust(width)
    return s.ljust(width)


def _render_box_table(
    headers: list[str],
    rows: list[list[str]],
    widths: list[int],
    aligns: list[str],
) -> list[str]:
    """Render a Unicode-box table. Wraps cell content to the given column widths."""

    def _border(left: str, mid: str, right: str, fill: str = "─") -> str:
        return left + mid.join(fill * (w + 2) for w in widths) + right

    def _row_lines(cells: list[str]) -> list[str]:
        wrapped = [_wrap_cell(cells[i], widths[i]) for i in range(len(widths))]
        height = max((len(c) for c in wrapped), default=1)
        for col in wrapped:
            while len(col) < height:
                col.append("")
        out_lines: list[str] = []
        for r in range(height):
            parts = [
                " " + _pad_cell(wrapped[c][r], widths[c], aligns[c]) + " "
                for c in range(len(widths))
            ]
            out_lines.append("│" + "│".join(parts) + "│")
        return out_lines

    out: list[str] = []
    out.append(_border("┌", "┬", "┐"))
    out.extend(_row_lines(headers))
    out.append(_border("├", "┼", "┤"))
    for i, row in enumerate(rows):
        if i > 0:
            out.append(_border("├", "┼", "┤"))
        out.extend(_row_lines(row))
    out.append(_border("└", "┴", "┘"))
    return out


# Column widths for the steps table (plain text). Total visible width ≈ 95 chars.
_STEP_TABLE_WIDTHS = [4, 6, 65, 9]
_STEP_TABLE_ALIGNS = ["center", "right", "left", "center"]
_STEP_TABLE_HEADERS = ["Step", "Time", "What the Agent Did", "Result"]


def _append_per_step_table(
    lines: list[str],
    history: AgentHistoryList,
    *,
    section_heading: str,
) -> None:
    """Render this history as a Step / Time / What / Result table."""
    lines.append("")
    lines.append(section_heading)
    if not history.history:
        lines.append("  (no steps recorded)")
        return

    rows: list[list[str]] = []
    for idx, h in enumerate(history.history):
        n = idx + 1
        dur_s = ""
        if h.metadata is not None:
            try:
                dur_s = f"{float(h.metadata.duration_seconds):.1f}s"
            except (TypeError, ValueError, AttributeError):
                pass
        what = _step_what_text(h)
        eval_text = ""
        if h.model_output:
            eval_text = h.model_output.evaluation_previous_goal or ""
        result = _verdict_label_plain(eval_text)
        rows.append([str(n), dur_s or "—", what, result])

    lines.extend(
        _render_box_table(
            _STEP_TABLE_HEADERS,
            rows,
            _STEP_TABLE_WIDTHS,
            _STEP_TABLE_ALIGNS,
        )
    )
    lines.append(f"(end of trace — {len(history.history)} steps)")


def _append_per_step_trace(
    lines: list[str],
    history: AgentHistoryList,
    *,
    section_heading: str,
    compact: bool = True,
    eval_max: int = 520,
    memory_max: int = 520,
    goal_max: int = 420,
    err_max: int = 360,
) -> None:
    """One block per browser-use iteration."""
    lines.append("")
    lines.append(section_heading)
    if not history.history:
        lines.append("  (no steps recorded)")
        return

    for idx, h in enumerate(history.history):
        n = idx + 1
        st = getattr(h, "state", None)
        url = (getattr(st, "url", None) or "").strip() or "(no url)"
        title = (getattr(st, "title", None) or "").strip()

        dur_s = ""
        if h.metadata is not None:
            try:
                dur_s = f"{float(h.metadata.duration_seconds):.1f}s"
            except (TypeError, ValueError, AttributeError):
                pass

        if compact:
            dur_bit = f"{dur_s} | " if dur_s else ""
            title_bit = f" | {_snip(title, 44)}" if title else ""
            lines.append(f"Step {n} | {dur_bit}{_short_url(url)}{title_bit}")
            mo = h.model_output
            if mo:
                note = (mo.evaluation_previous_goal or "").strip() or (mo.memory or "").strip()
                if note:
                    lines.append(f"  {_snip(note, 260)}")
                lines.append(
                    f"  {_action_type_names(mo)} → {_outcome_compact_line(h, max_total=280)}"
                )
            else:
                lines.append("  (no model output for this step)")
                lines.append(f"  → {_outcome_compact_line(h, max_total=280)}")
        else:
            dur = f" | {dur_s}" if dur_s else ""
            lines.append(f"Step {n} | {url}{dur}")
            mo = h.model_output
            if mo:
                if mo.evaluation_previous_goal:
                    lines.append(f"  Eval: {_snip(mo.evaluation_previous_goal, eval_max)}")
                if mo.memory:
                    lines.append(f"  Memory: {_snip(mo.memory, memory_max)}")
                if mo.next_goal:
                    lines.append(f"  Next goal: {_snip(mo.next_goal, goal_max)}")
                lines.append(f"  Actions: {_action_type_names(mo)}")
            else:
                lines.append("  (no model output for this step)")
            for r in h.result:
                if r.error:
                    lines.append(f"  Action error: {_snip(str(r.error), err_max)}")
                if r.is_done:
                    lines.append(f"  Terminal done: success={r.success}")

    lines.append(f"(end of trace — {len(history.history)} steps)")


def build_scenario_report(
    *,
    login_history: AgentHistoryList,
    workflow_history: AgentHistoryList | None,
    login_ok: bool,
    login_override: bool,
) -> str:
    lines: list[str] = []
    lines.append("")
    lines.append("=" * 50)
    lines.append("SCENARIO REPORT (PASS / FAIL)")
    lines.append("=" * 50)

    # TC-01 (suite gate uses login_ok; may override agent verdict via URL check)
    _, tc_reason = _verdict_token(login_history)
    display = "PASS" if login_ok else "FAIL"
    note = tc_reason
    if login_ok and login_override:
        note = "URL-based override (agent reported failure but session appears authenticated)"

    lines.append(f"TC-01 LOGIN: {display} — {note}")
    lines.append(
        f"  agent: is_done={login_history.is_done()} | successful={login_history.is_successful()}"
    )

    _append_per_step_table(
        lines,
        login_history,
        section_heading="--- TC-01 LOGIN — steps ---",
    )

    # Workflow aggregate
    lines.append("")
    if workflow_history is None:
        lines.append("WORKFLOW (2–10): SKIPPED — login did not pass")
        lines.append("")
        lines.append("--- WORKFLOW — steps ---")
        lines.append("  (skipped — login gate failed)")
    else:
        wf_token, wf_reason = _verdict_token(workflow_history)
        lines.append(f"WORKFLOW (2–10): {wf_token} — {wf_reason}")
        lines.append(
            f"  agent: is_done={workflow_history.is_done()} | "
            f"successful={workflow_history.is_successful()} | "
            f"steps={workflow_history.number_of_steps()}"
        )

        err_pairs = _collect_step_errors(workflow_history)
        if err_pairs:
            lines.append(f"  browser-use step errors ({len(err_pairs)}):")
            for step_i, msg in err_pairs[:20]:
                short = msg.replace("\n", " ")[:200]
                lines.append(f"    - step {step_i}: {short}")
            if len(err_pairs) > 20:
                lines.append(f"    ... and {len(err_pairs) - 20} more")

        _append_per_step_table(
            lines,
            workflow_history,
            section_heading="--- WORKFLOW (2–10) — steps ---",
        )

        fr = workflow_history.final_result()
        lines.append("")
        lines.append("  --- Agent closing summary (FINAL SUMMARY prompt) ---")
        parsed = _parse_final_summary_lines(fr)
        if parsed:
            for excerpt, st in parsed:
                lines.append(f"    [{st}] {excerpt}")
        elif fr:
            lines.append("    (could not parse numbered statuses; see full trace for the raw message.)")
            lines.append(f"    Raw (truncated): {_snip(fr, 800)}")
        else:
            lines.append("    (no final_result text on last step)")

    lines.append("=" * 50)
    return "\n".join(lines)


def _summarize_interacted_elements_for_report(value: Any) -> Any:
    """Replace heavy DOM blobs with short labels (name/type/placeholder)."""
    if not isinstance(value, list):
        return value
    out: list[str | None] = []
    for el in value:
        if el is None:
            out.append(None)
            continue
        if isinstance(el, dict):
            attrs = el.get("attributes") or {}
            hint = (
                attrs.get("name")
                or attrs.get("type")
                or (attrs.get("placeholder") or "")[:48]
                or attrs.get("id")
                or "element"
            )
            ax = el.get("ax_name") or ""
            line = f"{hint}" + (f" — {ax}" if ax else "")
            out.append(line[:160] + ("..." if len(line) > 160 else ""))
        else:
            out.append("(element)")
    return out


def _sanitize_history_dump_for_report(obj: Any, *, depth: int = 0) -> Any:
    """Shrink browser-use dumps for email/files: no DOM trees, no base64 images."""
    if depth > 40:
        return "<max depth>"
    if isinstance(obj, dict):
        cleaned: dict[str, Any] = {}
        for key, val in obj.items():
            if key == "state_message":
                cleaned[key] = "<omitted — see per-step trace in the main report>"
                continue
            if key == "interacted_element":
                cleaned[key] = _summarize_interacted_elements_for_report(val)
                continue
            if key == "images" and isinstance(val, list):
                cleaned[key] = []
                for item in val:
                    if isinstance(item, dict):
                        cleaned[key].append(
                            {"name": item.get("name", "?"), "data": "<base64 omitted>"}
                        )
                    else:
                        cleaned[key].append(item)
                continue
            if key == "reasoning" and isinstance(val, str) and len(val) > 900:
                cleaned[key] = val[:900] + "..."
                continue
            if key == "extracted_content" and isinstance(val, str) and len(val) > 3000:
                rest = len(val) - 3000
                cleaned[key] = val[:3000] + f"\n... ({rest} more characters omitted)"
                continue
            if key == "long_term_memory" and isinstance(val, str) and len(val) > 2000:
                cleaned[key] = val[:2000] + "..."
                continue
            cleaned[key] = _sanitize_history_dump_for_report(val, depth=depth + 1)
        return cleaned
    if isinstance(obj, list):
        return [_sanitize_history_dump_for_report(x, depth=depth + 1) for x in obj]
    return obj


def format_history_appendix_readable(history: AgentHistoryList, *, heading: str) -> str:
    """
    Structured history as JSON (for debugging). DOM trees and state_message blobs are
    stripped or shortened by _sanitize_history_dump_for_report.
    """
    raw = history.model_dump()
    safe = _sanitize_history_dump_for_report(raw)
    body = json.dumps(safe, indent=2, ensure_ascii=False, default=str)
    sep = "=" * 50
    return f"\n\n{sep}\n{heading}\n{sep}\n{body}\n"


# ---------------------------------------------------------------------------
# HTML report (used by email body)
# ---------------------------------------------------------------------------

# Color palette (kept inline so we don't depend on email-client CSS support).
_C_SUCCESS = "#16a34a"
_C_FAILURE = "#dc2626"
_C_UNCERTAIN = "#d97706"
_C_NEUTRAL = "#6b7280"
_C_TEXT = "#1f2937"
_C_MUTED = "#6b7280"
_C_BORDER = "#e5e7eb"
_C_HEAD_BG = "#f3f4f6"
_C_CARD_BG = "#f9fafb"


def _esc(s: str | None) -> str:
    return html.escape(s or "", quote=True)


def _verdict_from_eval(text: str | None) -> tuple[str, str, str]:
    """Parse `Verdict: Success/Failure/Uncertain` (or similar) from eval text.

    Returns (label, color_hex, emoji).
    """
    if not text:
        return ("—", _C_NEUTRAL, "")

    m = re.search(r"verdict\s*:\s*([A-Za-z]+)", text, re.IGNORECASE)
    if m:
        word = m.group(1).lower()
    else:
        low = text.lower()
        if "fail" in low or "error" in low:
            word = "failure"
        elif "uncertain" in low or "partial" in low:
            word = "uncertain"
        elif "success" in low or "succeeded" in low:
            word = "success"
        else:
            word = ""

    if word in ("success", "succeeded", "pass", "passed", "ok", "complete", "completed"):
        return ("Success", _C_SUCCESS, "✅")
    if word in ("failure", "failed", "fail", "error"):
        return ("Failure", _C_FAILURE, "❌")
    if word in ("uncertain", "partial"):
        return ("Uncertain", _C_UNCERTAIN, "⚠️")
    return ("—", _C_NEUTRAL, "")


def _step_eval_clean(eval_text: str | None) -> str:
    """Eval text with any trailing `Verdict: ...` clause removed (avoids duplication)."""
    if not eval_text:
        return ""
    cleaned = re.sub(r"verdict\s*:.*$", "", eval_text, flags=re.IGNORECASE).strip()
    return cleaned.rstrip(".").strip()


def _history_rows_html(history: AgentHistoryList | None) -> str:
    if history is None or not history.history:
        return ""

    rows: list[str] = []
    for idx, h in enumerate(history.history):
        n = idx + 1
        st = getattr(h, "state", None)
        url = (getattr(st, "url", None) or "").strip()
        title = (getattr(st, "title", None) or "").strip()

        dur_s = ""
        if h.metadata is not None:
            try:
                dur_s = f"{float(h.metadata.duration_seconds):.1f}s"
            except (TypeError, ValueError, AttributeError):
                pass

        eval_text = ""
        if h.model_output:
            eval_text = h.model_output.evaluation_previous_goal or ""
        label, color, emoji = _verdict_from_eval(eval_text)

        eval_clean = _esc(_snip(_step_eval_clean(eval_text), 320))
        outcome = _esc(_snip(_outcome_compact_line(h, max_total=240), 240))

        # Build "What the Agent Did" cell:
        # - main: cleaned eval text
        # - secondary: action outcome line (muted)
        # - context: page URL + title (muted, monospace)
        bits: list[str] = []
        if eval_clean:
            bits.append(f"<div style=\"color:{_C_TEXT};\">{eval_clean}</div>")
        if outcome and outcome != "—":
            bits.append(
                f"<div style=\"color:{_C_MUTED};font-size:12px;margin-top:3px;\">{outcome}</div>"
            )
        if url:
            page_line = (
                f"<div style=\"color:{_C_MUTED};font-size:11px;margin-top:4px;"
                "font-family:Consolas,Monaco,monospace;word-break:break-all;\">"
                f"{_esc(_short_url(url, max_len=70))}"
            )
            if title:
                page_line += f" <span style=\"color:#9ca3af;\">· {_esc(_snip(title, 48))}</span>"
            page_line += "</div>"
            bits.append(page_line)
        if not bits:
            bits.append(
                f"<span style=\"color:{_C_MUTED};font-style:italic;\">(no detail)</span>"
            )
        summary_html = "".join(bits)

        rows.append(
            "<tr>"
            f"<td style=\"padding:8px 10px;border:1px solid {_C_BORDER};text-align:center;"
            f"font-weight:600;color:{_C_TEXT};vertical-align:top;\">{n}</td>"
            f"<td style=\"padding:8px 10px;border:1px solid {_C_BORDER};color:{_C_TEXT};"
            f"white-space:nowrap;vertical-align:top;text-align:center;\">{_esc(dur_s) or '—'}</td>"
            f"<td style=\"padding:8px 10px;border:1px solid {_C_BORDER};line-height:1.45;"
            f"vertical-align:top;\">{summary_html}</td>"
            f"<td style=\"padding:8px 10px;border:1px solid {_C_BORDER};text-align:center;"
            f"white-space:nowrap;color:{color};font-weight:600;vertical-align:top;\">"
            f"{emoji} {_esc(label)}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def _steps_table_html(rows: str) -> str:
    if not rows:
        return (
            f"<p style=\"color:{_C_MUTED};font-style:italic;font-size:13px;\">"
            "(no steps recorded)</p>"
        )
    return (
        "<table cellpadding=\"0\" cellspacing=\"0\" border=\"0\" "
        "style=\"border-collapse:collapse;width:100%;"
        "font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;font-size:13px;\">"
        "<thead><tr style=\"background:" + _C_HEAD_BG + ";\">"
        f"<th style=\"padding:9px 10px;border:1px solid {_C_BORDER};text-align:center;"
        f"color:{_C_TEXT};font-weight:600;width:46px;\">Step</th>"
        f"<th style=\"padding:9px 10px;border:1px solid {_C_BORDER};text-align:center;"
        f"color:{_C_TEXT};font-weight:600;width:68px;\">Time</th>"
        f"<th style=\"padding:9px 10px;border:1px solid {_C_BORDER};text-align:left;"
        f"color:{_C_TEXT};font-weight:600;\">What the Agent Did</th>"
        f"<th style=\"padding:9px 10px;border:1px solid {_C_BORDER};text-align:center;"
        f"color:{_C_TEXT};font-weight:600;width:110px;\">Result</th>"
        "</tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )


def _summary_card_html(label: str, value: str, value_color: str, note: str) -> str:
    return (
        f"<td style=\"vertical-align:top;width:50%;background:{_C_CARD_BG};"
        f"border:1px solid {_C_BORDER};border-radius:6px;padding:12px;\">"
        f"<div style=\"color:{_C_MUTED};font-size:11px;text-transform:uppercase;"
        "letter-spacing:0.5px;font-weight:600;\">"
        f"{_esc(label)}</div>"
        f"<div style=\"font-size:22px;font-weight:700;color:{value_color};margin:4px 0;\">"
        f"{_esc(value)}</div>"
        f"<div style=\"color:{_C_TEXT};font-size:13px;line-height:1.4;\">{_esc(note)}</div>"
        "</td>"
    )


def _section_heading_html(title: str) -> str:
    return (
        f"<h3 style=\"font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;"
        f"font-size:15px;margin:22px 0 10px;color:{_C_TEXT};"
        f"border-left:4px solid #2563eb;padding:2px 0 2px 10px;\">{_esc(title)}</h3>"
    )


def build_scenario_report_html(
    *,
    run_id: str,
    login_history: AgentHistoryList,
    workflow_history: AgentHistoryList | None,
    login_ok: bool,
    login_override: bool,
) -> str:
    """Pretty HTML version of the scenario report. Suitable for use as the email HTML body."""

    _, tc_reason = _verdict_token(login_history)
    login_display = "PASS" if login_ok else "FAIL"
    login_color = _C_SUCCESS if login_ok else _C_FAILURE
    login_note = tc_reason
    if login_ok and login_override:
        login_note = (
            "URL-based override (agent reported failure but session appears authenticated)"
        )

    if workflow_history is None:
        wf_display = "SKIPPED"
        wf_color = _C_NEUTRAL
        wf_note = "login did not pass — downstream steps were not executed"
    else:
        wf_tok, wf_reason = _verdict_token(workflow_history)
        wf_display = wf_tok
        wf_color = {
            "PASS": _C_SUCCESS,
            "FAIL": _C_FAILURE,
            "INCOMPLETE": _C_UNCERTAIN,
        }.get(wf_tok, _C_NEUTRAL)
        wf_note = wf_reason

    parts: list[str] = []
    parts.append("<!DOCTYPE html><html><head><meta charset=\"utf-8\">")
    parts.append("<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">")
    parts.append("</head>")
    parts.append(
        "<body style=\"font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;"
        "background:#fafafa;padding:20px;color:" + _C_TEXT + ";margin:0;\">"
    )
    parts.append(
        "<div style=\"max-width:1000px;margin:0 auto;background:#ffffff;"
        f"border:1px solid {_C_BORDER};border-radius:8px;padding:22px;\">"
    )

    # Header
    parts.append(
        "<h2 style=\"margin:0 0 4px;color:" + _C_TEXT + ";font-size:20px;\">"
        "Scenario Report (PASS / FAIL)</h2>"
        f"<div style=\"color:{_C_MUTED};font-size:13px;margin-bottom:18px;\">"
        f"Run ID: <code style=\"background:{_C_HEAD_BG};padding:1px 6px;border-radius:4px;\">"
        f"{_esc(run_id)}</code></div>"
    )

    # Summary cards
    parts.append(
        "<table cellspacing=\"0\" cellpadding=\"0\" border=\"0\" "
        "style=\"border-collapse:separate;border-spacing:10px 0;"
        "margin:0 -10px 8px;width:calc(100% + 20px);\">"
        "<tr>"
    )
    parts.append(_summary_card_html("TC-01 Login", login_display, login_color, login_note))
    parts.append(
        _summary_card_html("Workflow (Steps 2–10)", wf_display, wf_color, wf_note)
    )
    parts.append("</tr></table>")

    # Login table
    parts.append(_section_heading_html("TC-01 LOGIN — Steps"))
    parts.append(_steps_table_html(_history_rows_html(login_history)))

    # Workflow table
    parts.append(_section_heading_html("WORKFLOW (Steps 2–10)"))
    if workflow_history is None:
        parts.append(
            f"<p style=\"color:#92400e;background:#fef3c7;border:1px solid #fde68a;"
            "padding:10px 12px;border-radius:6px;font-size:13px;margin:0;\">"
            "Skipped — login gate failed.</p>"
        )
    else:
        parts.append(_steps_table_html(_history_rows_html(workflow_history)))

        err_pairs = _collect_step_errors(workflow_history)
        if err_pairs:
            parts.append(
                f"<h4 style=\"margin:18px 0 6px;font-size:13px;color:{_C_FAILURE};\">"
                f"Step Errors ({len(err_pairs)})</h4>"
            )
            parts.append(
                f"<ul style=\"margin:0;padding-left:20px;color:{_C_TEXT};"
                "font-size:12px;line-height:1.6;\">"
            )
            for step_i, msg in err_pairs[:20]:
                short = _esc(msg.replace("\n", " ")[:200])
                parts.append(f"<li>Step {step_i}: {short}</li>")
            if len(err_pairs) > 20:
                parts.append(f"<li>… and {len(err_pairs) - 20} more</li>")
            parts.append("</ul>")

        fr = workflow_history.final_result()
        parsed = _parse_final_summary_lines(fr)
        if parsed:
            parts.append(_section_heading_html("Agent Closing Summary"))
            parts.append(
                "<table cellpadding=\"0\" cellspacing=\"0\" border=\"0\" "
                "style=\"border-collapse:collapse;width:100%;"
                "font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;"
                "font-size:13px;\">"
                f"<thead><tr style=\"background:{_C_HEAD_BG};\">"
                f"<th style=\"padding:8px 10px;border:1px solid {_C_BORDER};text-align:left;"
                f"color:{_C_TEXT};font-weight:600;\">Item</th>"
                f"<th style=\"padding:8px 10px;border:1px solid {_C_BORDER};text-align:center;"
                f"color:{_C_TEXT};font-weight:600;width:110px;\">Status</th>"
                "</tr></thead><tbody>"
            )
            for excerpt, st in parsed:
                color = {
                    "PASS": _C_SUCCESS,
                    "FAIL": _C_FAILURE,
                    "SKIP": _C_UNCERTAIN,
                }.get(st, _C_NEUTRAL)
                emoji = {
                    "PASS": "✅",
                    "FAIL": "❌",
                    "SKIP": "⚠️",
                }.get(st, "•")
                parts.append(
                    "<tr>"
                    f"<td style=\"padding:8px 10px;border:1px solid {_C_BORDER};"
                    f"color:{_C_TEXT};\">{_esc(excerpt)}</td>"
                    f"<td style=\"padding:8px 10px;border:1px solid {_C_BORDER};"
                    f"text-align:center;font-weight:600;color:{color};\">"
                    f"{emoji} {st}</td>"
                    "</tr>"
                )
            parts.append("</tbody></table>")

    parts.append(
        f"<div style=\"margin-top:24px;padding-top:12px;border-top:1px solid {_C_BORDER};"
        f"color:{_C_MUTED};font-size:11px;text-align:center;\">"
        "Generated by FloTorch QA Automation · Full plain-text trace is attached."
        "</div>"
    )
    parts.append("</div></body></html>")
    return "".join(parts)
