"""Summarize pass/fail for TC-01 login and the post-login workflow (Steps 2–10)."""

from __future__ import annotations

import html
import re
from typing import Any

from browser_use.agent.views import AgentHistoryList


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


def _status_from_summary_token(word: str) -> str:
    w = word.upper()
    if w in ("PASS", "PASSED", "COMPLETE", "COMPLETED", "OK", "SUCCESS", "SUCCEEDED"):
        return "PASS"
    if w in ("FAIL", "FAILED", "ERROR"):
        return "FAIL"
    if w in ("SKIP", "SKIPPED"):
        return "SKIP"
    return "UNKNOWN"


def _parse_final_summary_lines(final_text: str | None) -> list[tuple[str, str]]:
    """
    Best-effort parse of FINAL SUMMARY bullets (numbered lines).
    Returns (line excerpt, guessed status).

    Excerpt always ends with " — {status}" so long playground lines do not look
    like a blank status when PASS/FAIL was truncated off the end.
    """
    if not final_text or not final_text.strip():
        return []

    status_words = re.compile(
        r"\b(PASS|PASSED|FAIL|FAILED|SKIP|SKIPPED|ERROR|COMPLETE|COMPLETED|OK|SUCCESS|SUCCEEDED)\b",
        re.IGNORECASE,
    )
    placeholder = re.compile(r"PASS\s*/\s*FAIL", re.IGNORECASE)
    rows: list[tuple[str, str]] = []
    max_body = 200

    for raw_line in final_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if not re.match(r"^\d+\.", line):
            continue

        separator: str | None = None
        tail = line
        if "—" in line:
            separator = "—"
            tail = line.rsplit("—", 1)[-1].strip()
        elif re.search(r"\s[-–]\s", line):
            separator = "-"
            tail = line.rsplit("-", 1)[-1].strip()

        m = None if placeholder.search(tail) else status_words.search(tail)
        body = line
        if m and separator:
            body = line.rsplit(separator, 1)[0].strip()
        if not m:
            m = status_words.search(line)
            body = line

        if not m:
            excerpt = line[:max_body] + ("..." if len(line) > max_body else "")
            rows.append((excerpt, "UNKNOWN"))
            continue

        status = _status_from_summary_token(m.group(1))
        if len(body) > max_body:
            body = body[: max_body - 3] + "..."
        excerpt = f"{body} — {status}"
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


def _append_gate_failed_phase(lines: list[str], *, title: str, reason: str) -> None:
    """Mark a phase FAIL because a suite gate (e.g. login) did not pass."""
    lines.append("")
    lines.append(f"{title}: FAIL — {reason}")
    lines.append("")
    lines.append(f"--- {title} — steps ---")
    lines.append("  (not executed — blocked by suite gate)")


def _append_login_gate_failed_phases(
    lines: list[str],
    *,
    workflow_mode: str = "full",
    reason: str,
    report_ctx: Any = None,
    execution_modules=None,
) -> None:
    from FloTorch.prompts.tasks import suite_phase_titles_for_report

    for title in suite_phase_titles_for_report(
        workflow_mode=workflow_mode,
        ctx=report_ctx,
        execution_modules=execution_modules,
    ):
        _append_gate_failed_phase(lines, title=title, reason=reason)


def _report_phase_entries(
    *,
    login_ok: bool,
    org_history: AgentHistoryList | None,
    workspace_history: AgentHistoryList | None,
    extra_phases: list[tuple[str, AgentHistoryList | None]] | None,
    workflow_history: AgentHistoryList | None,
) -> list[tuple[str, AgentHistoryList | None, str | None]]:
    """Ordered (title, history, skip_reason) for overview and suite verdict."""
    if not login_ok:
        return []
    entries: list[tuple[str, AgentHistoryList | None, str | None]] = []
    if org_history is not None:
        entries.append(("Phase 2 — Org provider", org_history, None))
    if workspace_history is not None:
        entries.append(("Phase 3 — Workspace", workspace_history, None))
    if extra_phases:
        for title, hist in extra_phases:
            entries.append((title, hist, None))
    elif workflow_history is not None:
        entries.append(("Workspace-level tasks", workflow_history, None))
    elif workspace_history is not None:
        entries.append(
            (
                "Workspace-level tasks",
                None,
                "workspace gate failed or phases not run",
            )
        )
    return entries


def _phase_status_token(
    history: AgentHistoryList | None,
    skipped_reason: str | None = None,
) -> tuple[str, str]:
    if history is None:
        return "SKIPPED", skipped_reason or "not executed"
    return _verdict_token(history)


def _suite_verdict(
    *,
    login_ok: bool,
    phase_entries: list[tuple[str, AgentHistoryList | None, str | None]],
) -> tuple[str, str]:
    if not login_ok:
        return "FAIL", "TC-01 login gate failed — suite aborted"
    if not phase_entries:
        return "PASS", "login only (no downstream phases recorded)"
    tokens = [_phase_status_token(h, skip)[0] for _, h, skip in phase_entries]
    if "FAIL" in tokens:
        return "FAIL", "one or more phases reported failure"
    if "INCOMPLETE" in tokens:
        return "INCOMPLETE", "one or more phases did not finish cleanly"
    if all(t == "SKIPPED" for t in tokens):
        return "SKIPPED", "downstream phases were not executed"
    return "PASS", "all executed phases passed"


def _append_run_metadata(
    lines: list[str],
    *,
    run_id: str | None,
    workspace_name: str | None,
    plan_label: str | None,
) -> None:
    if not any((run_id, workspace_name, plan_label)):
        return
    lines.append("RUN")
    if run_id:
        lines.append(f"  Run ID:    {run_id}")
    if workspace_name:
        lines.append(f"  Workspace: {workspace_name}")
    if plan_label:
        lines.append(f"  Plan:      {plan_label}")
    lines.append("")


def _append_phase_overview(
    lines: list[str],
    phase_entries: list[tuple[str, AgentHistoryList | None, str | None]],
) -> None:
    if not phase_entries:
        return
    lines.append("EXECUTION OVERVIEW (phase → result)")
    lines.append("-" * 50)
    for title, hist, skip in phase_entries:
        tok, reason = _phase_status_token(hist, skip)
        steps = hist.number_of_steps() if hist else 0
        step_bit = f" · {steps} steps" if steps else ""
        lines.append(f"  {tok:11}  {title}{step_bit}")
        if tok in ("FAIL", "INCOMPLETE", "SKIPPED"):
            lines.append(f"             ({reason})")
    lines.append("-" * 50)


def _append_phase_block(
    lines: list[str],
    *,
    title: str,
    history: AgentHistoryList | None,
    skipped_reason: str | None = None,
) -> None:
    lines.append("")
    if history is None:
        reason = skipped_reason or "not executed"
        lines.append(f"{title}: SKIPPED — {reason}")
        lines.append("")
        lines.append(f"--- {title} — steps ---")
        lines.append("  (skipped)")
        return
    tok, reason = _verdict_token(history)
    lines.append(f"{title}: {tok} — {reason}")
    lines.append(
        f"  agent: is_done={history.is_done()} | "
        f"successful={history.is_successful()} | "
        f"steps={history.number_of_steps()}"
    )
    _append_per_step_table(lines, history, section_heading=f"--- {title} — steps ---")


def build_scenario_report(
    *,
    login_history: AgentHistoryList,
    workflow_history: AgentHistoryList | None,
    login_ok: bool,
    login_override: bool,
    workflow_mode: str = "full",
    org_history: AgentHistoryList | None = None,
    workspace_history: AgentHistoryList | None = None,
    extra_phases: list[tuple[str, AgentHistoryList | None]] | None = None,
    run_id: str | None = None,
    workspace_name: str | None = None,
    plan_label: str | None = None,
    report_ctx: Any = None,
    execution_modules=None,
) -> str:
    lines: list[str] = []
    lines.append("")
    lines.append("=" * 50)
    lines.append("SCENARIO REPORT (PASS / FAIL)")
    lines.append("=" * 50)
    _append_run_metadata(
        lines,
        run_id=run_id,
        workspace_name=workspace_name,
        plan_label=plan_label,
    )

    phase_entries = _report_phase_entries(
        login_ok=login_ok,
        org_history=org_history,
        workspace_history=workspace_history,
        extra_phases=extra_phases,
        workflow_history=workflow_history,
    )
    suite_tok, suite_reason = _suite_verdict(login_ok=login_ok, phase_entries=phase_entries)
    lines.append(f"SUITE VERDICT: {suite_tok} — {suite_reason}")
    if login_ok and phase_entries:
        _append_phase_overview(lines, phase_entries)

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

    if not login_ok:
        from FloTorch.prompts.tasks import LOGIN_GATE_FAILED_REASON

        lines.append("")
        lines.append(
            "SUITE GATE: TC-01 login did not pass — all phases below are FAIL (not executed)."
        )
        _append_login_gate_failed_phases(
            lines,
            workflow_mode=workflow_mode,
            reason=LOGIN_GATE_FAILED_REASON,
            report_ctx=report_ctx,
            execution_modules=execution_modules,
        )
    else:
        if org_history is not None:
            _append_phase_block(lines, title="PHASE 2 — Org provider", history=org_history)
        if workspace_history is not None:
            _append_phase_block(lines, title="PHASE 3 — Workspace", history=workspace_history)

        if extra_phases:
            for title, hist in extra_phases:
                _append_phase_block(lines, title=title, history=hist)
        elif workflow_history is not None:
            _append_phase_block(
                lines,
                title="PHASE 4+ — Workspace-level tasks",
                history=workflow_history,
            )
        elif workspace_history is not None:
            _append_phase_block(
                lines,
                title="PHASE 4+ — Workspace-level tasks",
                history=None,
                skipped_reason="workspace gate failed or phases not run",
            )

        close_hist = workflow_history
        if close_hist is not None:
            fr = close_hist.final_result()
            lines.append("")
            lines.append("  --- Suite close / FINAL SUMMARY ---")
            parsed = _parse_final_summary_lines(fr)
            if parsed:
                for excerpt, st in parsed:
                    lines.append(f"    [{st}] {excerpt}")
            elif fr:
                lines.append(f"    Raw (truncated): {_snip(fr, 800)}")
            err_pairs = _collect_step_errors(close_hist)
            if err_pairs:
                lines.append(f"  Close-phase step errors ({len(err_pairs)}):")
                for step_i, msg in err_pairs[:10]:
                    lines.append(f"    - step {step_i}: {msg.replace(chr(10), ' ')[:200]}")

    lines.append("=" * 50)
    return "\n".join(lines)


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


def _verdict_color(token: str) -> str:
    return {
        "PASS": _C_SUCCESS,
        "FAIL": _C_FAILURE,
        "INCOMPLETE": _C_UNCERTAIN,
        "SKIPPED": _C_NEUTRAL,
        "N/A": _C_NEUTRAL,
    }.get(token, _C_NEUTRAL)


def _phase_overview_table_html(
    phase_entries: list[tuple[str, AgentHistoryList | None, str | None]],
) -> str:
    if not phase_entries:
        return ""
    rows: list[str] = []
    for title, hist, skip in phase_entries:
        tok, reason = _phase_status_token(hist, skip)
        steps = hist.number_of_steps() if hist else 0
        step_cell = str(steps) if steps else "—"
        color = _verdict_color(tok)
        rows.append(
            "<tr>"
            f"<td style=\"padding:8px 10px;border:1px solid {_C_BORDER};\">{_esc(title)}</td>"
            f"<td style=\"padding:8px 10px;border:1px solid {_C_BORDER};text-align:center;\">"
            f"{step_cell}</td>"
            f"<td style=\"padding:8px 10px;border:1px solid {_C_BORDER};text-align:center;"
            f"font-weight:600;color:{color};\">{tok}</td>"
            f"<td style=\"padding:8px 10px;border:1px solid {_C_BORDER};color:{_C_MUTED};"
            f"font-size:12px;\">{_esc(reason)}</td>"
            "</tr>"
        )
    return (
        "<table cellpadding=\"0\" cellspacing=\"0\" border=\"0\" "
        "style=\"border-collapse:collapse;width:100%;margin:0 0 16px;"
        "font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;font-size:13px;\">"
        f"<thead><tr style=\"background:{_C_HEAD_BG};\">"
        f"<th style=\"padding:8px 10px;border:1px solid {_C_BORDER};text-align:left;\">Phase</th>"
        f"<th style=\"padding:8px 10px;border:1px solid {_C_BORDER};text-align:center;width:56px;\">"
        "Steps</th>"
        f"<th style=\"padding:8px 10px;border:1px solid {_C_BORDER};text-align:center;width:90px;\">"
        "Result</th>"
        f"<th style=\"padding:8px 10px;border:1px solid {_C_BORDER};text-align:left;\">Note</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _phase_verdict_badge_html(history: AgentHistoryList | None, skipped_reason: str | None) -> str:
    tok, reason = _phase_status_token(history, skipped_reason)
    color = _verdict_color(tok)
    return (
        f"<p style=\"margin:0 0 8px;font-size:13px;\">"
        f"<strong style=\"color:{color};\">{tok}</strong>"
        f"<span style=\"color:{_C_MUTED};\"> — {_esc(reason)}</span></p>"
    )


def build_scenario_report_html(
    *,
    run_id: str,
    login_history: AgentHistoryList,
    workflow_history: AgentHistoryList | None,
    login_ok: bool,
    login_override: bool,
    workflow_mode: str = "full",
    org_history: AgentHistoryList | None = None,
    workspace_history: AgentHistoryList | None = None,
    extra_phases: list[tuple[str, AgentHistoryList | None]] | None = None,
    workspace_name: str | None = None,
    plan_label: str | None = None,
    report_ctx: Any = None,
    execution_modules=None,
) -> str:
    """Pretty HTML version of the scenario report. Suitable for use as the email HTML body."""

    phase_entries = _report_phase_entries(
        login_ok=login_ok,
        org_history=org_history,
        workspace_history=workspace_history,
        extra_phases=extra_phases,
        workflow_history=workflow_history,
    )
    suite_tok, suite_reason = _suite_verdict(login_ok=login_ok, phase_entries=phase_entries)
    suite_color = _verdict_color(suite_tok)

    close_label = "Suite close"
    if extra_phases:
        close_label = extra_phases[-1][0]
    elif workflow_history is not None:
        close_label = "Workspace-level tasks"

    _, tc_reason = _verdict_token(login_history)
    login_display = "PASS" if login_ok else "FAIL"
    login_color = _C_SUCCESS if login_ok else _C_FAILURE
    login_note = tc_reason
    if login_ok and login_override:
        login_note = (
            "URL-based override (agent reported failure but session appears authenticated)"
        )

    if workflow_history is None:
        wf_display = suite_tok if login_ok else "FAIL"
        wf_color = suite_color if login_ok else _C_FAILURE
        wf_note = suite_reason if login_ok else "TC-01 login gate failed — suite aborted"
    else:
        wf_tok, wf_reason = _verdict_token(workflow_history)
        wf_display = wf_tok
        wf_color = _verdict_color(wf_tok)
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
        f"<div style=\"color:{_C_MUTED};font-size:13px;margin-bottom:6px;\">"
        f"Run ID: <code style=\"background:{_C_HEAD_BG};padding:1px 6px;border-radius:4px;\">"
        f"{_esc(run_id)}</code>"
    )
    if workspace_name:
        parts.append(
            f" &nbsp;·&nbsp; Workspace: <code style=\"background:{_C_HEAD_BG};"
            f"padding:1px 6px;border-radius:4px;\">{_esc(workspace_name)}</code>"
        )
    parts.append("</div>")
    if plan_label:
        parts.append(
            f"<div style=\"color:{_C_MUTED};font-size:12px;margin-bottom:14px;\">"
            f"{_esc(plan_label)}</div>"
        )
    else:
        parts.append("<div style=\"margin-bottom:14px;\"></div>")

    parts.append(
        f"<p style=\"margin:0 0 14px;font-size:14px;\">"
        f"<strong>Suite verdict:</strong> "
        f"<span style=\"color:{suite_color};font-weight:700;\">{suite_tok}</span>"
        f"<span style=\"color:{_C_MUTED};\"> — {_esc(suite_reason)}</span></p>"
    )
    if login_ok and phase_entries:
        parts.append(_section_heading_html("Execution overview"))
        parts.append(_phase_overview_table_html(phase_entries))

    # Summary cards
    parts.append(
        "<table cellspacing=\"0\" cellpadding=\"0\" border=\"0\" "
        "style=\"border-collapse:separate;border-spacing:10px 0;"
        "margin:0 -10px 8px;width:calc(100% + 20px);\">"
        "<tr>"
    )
    parts.append(_summary_card_html("TC-01 Login", login_display, login_color, login_note))
    parts.append(_summary_card_html(close_label, wf_display, wf_color, wf_note))
    parts.append("</tr></table>")

    # Login table
    parts.append(_section_heading_html("Phase 1 — TC-01 LOGIN"))
    parts.append(_steps_table_html(_history_rows_html(login_history)))

    if not login_ok:
        from FloTorch.prompts.tasks import (
            LOGIN_GATE_FAILED_REASON,
            suite_phase_titles_for_report,
        )

        parts.append(
            "<p style=\"color:#b91c1c;font-size:14px;font-weight:600;margin:18px 0 8px;\">"
            "Suite gate: TC-01 login did not pass — all phases below are FAIL (not executed)."
            "</p>"
        )
        parts.append(
            "<table cellpadding=\"0\" cellspacing=\"0\" border=\"0\" "
            "style=\"border-collapse:collapse;width:100%;margin-bottom:16px;"
            "font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;font-size:13px;\">"
            f"<thead><tr style=\"background:{_C_HEAD_BG};\">"
            f"<th style=\"padding:8px 10px;border:1px solid {_C_BORDER};text-align:left;\">Phase</th>"
            f"<th style=\"padding:8px 10px;border:1px solid {_C_BORDER};text-align:center;width:90px;\">"
            "Result</th></tr></thead><tbody>"
        )
        for title in suite_phase_titles_for_report(
            workflow_mode=workflow_mode,
            ctx=report_ctx,
            execution_modules=execution_modules,
        ):
            parts.append(
                "<tr>"
                f"<td style=\"padding:8px 10px;border:1px solid {_C_BORDER};\">{_esc(title)}</td>"
                f"<td style=\"padding:8px 10px;border:1px solid {_C_BORDER};text-align:center;"
                f"font-weight:600;color:{_C_FAILURE};\">FAIL</td>"
                "</tr>"
            )
        parts.append("</tbody></table>")
        parts.append(
            f"<p style=\"color:{_C_MUTED};font-size:12px;margin:0 0 12px;\">"
            f"{_esc(LOGIN_GATE_FAILED_REASON)}</p>"
        )

    if login_ok and org_history is not None:
        parts.append(_section_heading_html("Phase 2 — Org provider"))
        parts.append(_phase_verdict_badge_html(org_history, None))
        parts.append(_steps_table_html(_history_rows_html(org_history)))

    if login_ok and workspace_history is not None:
        parts.append(_section_heading_html("Phase 3 — Workspace"))
        parts.append(_phase_verdict_badge_html(workspace_history, None))
        parts.append(_steps_table_html(_history_rows_html(workspace_history)))

    if login_ok and extra_phases:
        for title, hist in extra_phases:
            parts.append(_section_heading_html(title))
            parts.append(_phase_verdict_badge_html(hist, None if hist else "skipped"))
            if hist is not None:
                parts.append(_steps_table_html(_history_rows_html(hist)))
    elif login_ok and workflow_history is not None:
        parts.append(_section_heading_html("Workspace-level tasks"))
        parts.append(_phase_verdict_badge_html(workflow_history, None))
        parts.append(_steps_table_html(_history_rows_html(workflow_history)))

    if workflow_history is not None:
        fr = workflow_history.final_result()
        parsed = _parse_final_summary_lines(fr)
        if parsed:
            parts.append(_section_heading_html("Suite close — Agent summary"))
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
        err_pairs = _collect_step_errors(workflow_history)
        if err_pairs:
            parts.append(
                f"<p style=\"color:{_C_FAILURE};font-size:13px;font-weight:600;"
                f"margin:12px 0 6px;\">Close-phase step errors ({len(err_pairs)})</p>"
            )
            parts.append("<ul style=\"margin:0 0 12px;padding-left:20px;font-size:12px;"
                         f"color:{_C_TEXT};\">")
            for step_i, msg in err_pairs[:10]:
                parts.append(
                    f"<li>step {step_i}: {_esc(msg.replace(chr(10), ' ')[:200])}</li>"
                )
            parts.append("</ul>")

    parts.append(
        f"<div style=\"margin-top:24px;padding-top:12px;border-top:1px solid {_C_BORDER};"
        f"color:{_C_MUTED};font-size:11px;text-align:center;\">"
        "Generated by FloTorch QA Automation · Full plain-text trace is attached."
        "</div>"
    )
    parts.append("</div></body></html>")
    return "".join(parts)
