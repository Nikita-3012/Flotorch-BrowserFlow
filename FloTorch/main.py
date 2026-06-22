import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Allow running as `python main.py` from inside `FloTorch/` by adding the
# repository root to sys.path so absolute imports like `FloTorch.*` resolve.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
_FLOTORCH_ROOT = Path(__file__).resolve().parent
# Load env before any LLM or FloTorch config so Gemini / console credentials resolve reliably.
load_dotenv(_FLOTORCH_ROOT / ".env")
load_dotenv()

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from browser_use import Agent, ChatGoogle
from browser_use.browser import BrowserSession

# Make sure stdout can print Unicode box-drawing chars used by the scenario table.
# On Windows, the default console codepage (cp1252) can't encode `─│┌┐` etc.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass

from FloTorch.runtime.browser_fullscreen import fullscreen_browser_window
from FloTorch.runtime.logging_utils import make_step_end_logger
from FloTorch.runtime.results_storage import save_scenario_reports
from FloTorch.config.execution_config import execution_modules_raw, read_execution_config
from FloTorch.config.providers import build_run_context
from FloTorch.reporting.scenario_report import build_scenario_report, build_scenario_report_html
from FloTorch.config.constants import (
    AGENT_EXTEND_SYSTEM_MESSAGE,
    WORKSPACE_GATE_FAILED_TOKEN,
)
from FloTorch.prompts.tasks import build_task_login
from FloTorch.runtime.async_cleanup import close_browser_session, run_async
from FloTorch.runtime.phase_utils import history_mentions_token

_DATASET_DIR = _FLOTORCH_ROOT / "Dataset"
# browser-use only allows upload_file for paths listed here (security allowlist).
def _workflow_dataset_paths() -> list[str]:
    names = (
        "llm-dataset.json",
        "prompt-without-kb.json",
        "anthropic-3qa-dataset.json",
        "3qa.json",
        "agent-1-delete.json",
    )
    return [str((_DATASET_DIR / n).resolve()) for n in names if (_DATASET_DIR / n).is_file()]


WORKFLOW_AVAILABLE_FILE_PATHS = _workflow_dataset_paths()


async def _run_agent_phase(
    *,
    label: str,
    task: str,
    llm: ChatGoogle,
    browser_session: BrowserSession,
    max_steps: int,
    watch_workspace_fallback: bool = False,
    available_file_paths: list[str] | None = None,
):
    from browser_use import Agent

    print(f"\n{'=' * 50}")
    print(label)
    print("=" * 50)
    kwargs: dict = {
        "task": task,
        "llm": llm,
        "browser_session": browser_session,
        "max_actions_per_step": 5,
        "use_vision": True,
        "extend_system_message": AGENT_EXTEND_SYSTEM_MESSAGE,
    }
    if available_file_paths is not None:
        kwargs["available_file_paths"] = available_file_paths
    agent = Agent(**kwargs)
    short_label = label.split(":", 1)[0].strip() if ":" in label else label
    history = await agent.run(
        max_steps=max_steps,
        on_step_end=make_step_end_logger(
            short_label,
            watch_workspace_fallback=watch_workspace_fallback,
        ),
    )
    print(f"\n{label} — complete")
    print(f"  is_done: {history.is_done()} | is_successful: {history.is_successful()}")
    return history


def _is_login_url(url: str) -> bool:
    u = (url or "").lower().strip()
    return "/auth/signin" in u or "/auth/login" in u or u.endswith("/auth")


async def _ensure_authenticated(
    *,
    llm: ChatGoogle,
    browser_session: BrowserSession,
    ctx,
) -> bool:
    """Re-run login once if the browser is currently on auth pages."""
    current_url = ""
    try:
        current_url = (await browser_session.get_current_page_url() or "").strip()
    except Exception:
        current_url = ""
    if current_url and not _is_login_url(current_url):
        return True

    print("Session appears unauthenticated before phase. Re-running TC-01 login recovery...")
    login_agent = Agent(
        task=build_task_login(ctx),
        llm=llm,
        browser_session=browser_session,
        max_actions_per_step=5,
        use_vision=True,
        max_failures=4,
        extend_system_message=AGENT_EXTEND_SYSTEM_MESSAGE,
    )
    login_history = await login_agent.run(
        max_steps=35,
        on_step_end=make_step_end_logger("TC-01 LOGIN RECOVERY"),
    )
    ok = login_history.is_done() and login_history.is_successful() is True
    print(
        f"Login recovery result: is_done={login_history.is_done()} | "
        f"is_successful={login_history.is_successful()}"
    )
    return ok


async def main():
    ctx = build_run_context()
    if not ctx.email or not ctx.password:
        print("ERROR: FLOTORCH_EMAIL and FLOTORCH_PASSWORD must be set in the environment.")
        raise SystemExit(1)

    task_login = build_task_login(ctx)

    # ── Read execution plan (execution.py) or fall back to .env workflow_mode ──
    _exec_modules = execution_modules_raw()
    _exec_config = read_execution_config()

    workflow_mode = (os.getenv("FLOTORCH_WORKFLOW") or "full").strip().lower()
    if workflow_mode == "guardrail":
        workflow_mode = "guardrails"
    if workflow_mode == "evaluation":
        workflow_mode = "evaluations"
    if workflow_mode == "workflow":
        workflow_mode = "workflow_evaluation"

    if _exec_modules is not None:
        print("Execution plan: execution.py")
        workflow_mode = "evaluations"  # reporting label when using execution.py
    _VALID_WORKFLOWS = (
        "full",
        "prompt_partials",
        "partials",
        "guardrails",
        "evaluations",
        "workflow_evaluation",
    )
    if workflow_mode not in _VALID_WORKFLOWS:
        print(
            f'ERROR: Unknown FLOTORCH_WORKFLOW="{workflow_mode}". '
            f'Use one of: {", ".join(_VALID_WORKFLOWS)}'
        )
        raise SystemExit(1)

    print(f"Workflow mode: {workflow_mode}")
    if workflow_mode == "full":
        print(
            "Execution order (gates):"
            "\n  1. TC-01 Login — HARD GATE (fail → abort suite, all cases FAIL)"
            "\n  2. Org provider — requires login PASS"
            "\n  3. Workspace create + enter"
            "\n  4–12. Workspace-scoped tests"
            "\n     (provider → models → vector → repos → datasets → evals → guardrails → partials → close)"
        )
    elif workflow_mode == "guardrails":
        print(
            "GUARDRAILS SUITE (one model only — guardrail-test-<run-id>):"
            "\n  1. Login → 2. Org provider → 3. Workspace"
            "\n  4. Sanity guardrails (4) → ONE model → Playground → Close"
            "\n  (No Step 6 two-model flow; no embedding model)"
        )
    elif workflow_mode == "evaluations":
        print(
            "EVALUATIONS SUITE:"
            "\n  1. Login → 2. Org provider → 3. Workspace"
            "\n  4. Workspace provider → Models + embedding → Vector (if .env) → Datasets"
            "\n  5. LLM eval → Prompt eval → RAG eval (if vector path) → Close"
            "\n  (No guardrails, no prompt partials)"
        )
    elif workflow_mode in ("prompt_partials", "partials"):
        print(
            "PROMPT PARTIALS SUITE:"
            "\n  1. Login → 2. Org provider → 3. Workspace"
            "\n  4. Chat models (Step 6) → 5. Prompt partials → Playground → Close"
        )
        print("  >>> Full suite: $env:FLOTORCH_WORKFLOW='full'")
    elif workflow_mode == "workflow_evaluation":
        print(
            "WORKFLOW EVALUATION SUITE:"
            "\n  1. Login → 2. Create + enter workspace (automation-<uid>)"
            "\n  3. Workflow canvas + Workflow Evaluation run"
            "\n  (No org provider, models, or datasets — prerequisites must exist)"
        )
    else:
        print(f'  >>> Unknown workflow "{workflow_mode}" — should not reach here.')

    gemini_key = (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()
    if not gemini_key:
        print(
            "ERROR: The browser agent uses Google Gemini. Set GOOGLE_API_KEY or GEMINI_API_KEY "
            "(e.g. in FloTorch/.env). FloTorch console login still uses FLOTORCH_EMAIL / FLOTORCH_PASSWORD."
        )
        raise SystemExit(1)

    llm = ChatGoogle(model="gemini-2.5-flash", api_key=gemini_key)

    # Maximized at native 100% scale (matches manual Chrome: tabs visible, taskbar stays up).
    # keep_alive=True: first Agent.run() must NOT call kill() on this session, or the next Agent
    # can hit "BrowserStateRequestEvent ... none did" (event bus / DOM watchdog out of sync). We kill in `finally` below.
    browser_session = BrowserSession(
        headless=False,
        keep_alive=True,
        args=["--start-maximized"],
    )

    print(f"\nWorkspace: {ctx.workspace_name}")
    print(
        f"Global Provider (name field): {ctx.org_provider_name or 'SKIPPED (no .env providers)'}"
    )
    print(
        f"Workspace Provider: {ctx.selected_second_provider['name'] if ctx.selected_second_provider else 'N/A'}"
    )
    print(f"Embedding: {ctx.embedding_provider['name'] if ctx.embedding_provider else 'N/A'}")
    print(f"Org provider type (priority): {ctx.org_provider_type or 'N/A'}")
    print(f"Vector fallback creates: {len(ctx.vector_providers_planned)} (max 1)")
    if ctx.org_verify_sections:
        print(f"Org provider verify sections: {', '.join(ctx.org_verify_sections)}")
    if ctx.vector_active_path:
        print(f"Vector RAG provider ref: {ctx.vector_active_path.get('provider_ref', 'N/A')}")
    if ctx.vector_providers_skipped:
        for line in ctx.vector_providers_skipped[:5]:
            print(f"  Vector note: {line}")
    print("Browser: maximized @ 100% scale (native UI size)")
    print("-" * 50)

    try:
        # --- Phase 1: TC-01 Login (hard gate) ---
        print("Phase 1: TC-01 LOGIN (credentials gate)\n")
        login_agent = Agent(
            task=task_login,
            llm=llm,
            browser_session=browser_session,
            max_actions_per_step=5,
            use_vision=True,
            max_failures=4,
            extend_system_message=AGENT_EXTEND_SYSTEM_MESSAGE,
        )
        login_history = await login_agent.run(
            max_steps=45,
            on_step_end=make_step_end_logger("TC-01 LOGIN"),
        )

        print("\n" + "=" * 50)
        print("TC-01 LOGIN — phase complete")
        print("=" * 50)
        print(f"  is_done: {login_history.is_done()}")
        print(f"  is_successful: {login_history.is_successful()}")
        if login_history.final_result():
            print(f"  agent final message: {login_history.final_result()}")

        login_ok = login_history.is_done() and login_history.is_successful() is True
        login_override = False
        if not login_ok:
            # Guard against false negatives from the LLM login verdict:
            # if the browser is already outside auth pages, continue the suite.
            current_url = ""
            try:
                current_url = (await browser_session.get_current_page_url() or "").lower().strip()
            except Exception:
                current_url = ""

            if current_url and not _is_login_url(current_url):
                print("\n" + "=" * 50)
                print("LOGIN OVERRIDE: Agent reported failure, but browser appears authenticated.")
                print(f"Current URL after TC-01: {current_url}")
                print("Continuing with Phases 2–4.")
                print("=" * 50)
                login_ok = True
                login_override = True

        if login_ok:
            if await fullscreen_browser_window(browser_session):
                print("Browser window maximized (post-login; taskbar visible).")
            else:
                print("Note: could not maximize browser via CDP; continuing with launch flags.")

        if not login_ok:
            print("\n" + "=" * 50)
            print("SUITE ABORTED: TC-01 LOGIN did not pass — skipping all downstream steps.")
            print("Fix credentials or account state, then re-run.")
            print("=" * 50)
            import FloTorch.prompts.tasks as task_builders

            plan_label = (
                task_builders.execution_plan_label(ctx, _exec_modules)
                if _exec_modules is not None
                else None
            )
            report_kwargs = dict(
                login_history=login_history,
                workflow_history=None,
                login_ok=False,
                login_override=False,
                workflow_mode=workflow_mode,
                run_id=ctx.uid,
                workspace_name=ctx.workspace_name,
                plan_label=plan_label,
                report_ctx=ctx,
                execution_modules=_exec_modules,
            )
            report_text = build_scenario_report(**report_kwargs)
            report_html = build_scenario_report_html(run_id=ctx.uid, **report_kwargs)
            print(report_text)
            out_path, html_path = save_scenario_reports(
                ctx.uid, report_text, report_html
            )
            print(f"\nSaved login-phase trace to {out_path}")
            print(f"Saved HTML report to {html_path}")
            return

        org_history = None
        workspace_history = None
        extra_phases: list = []
        close_history = None

        import FloTorch.prompts.tasks as task_builders

        if _exec_modules is not None:
            if isinstance(_exec_modules, str) and _exec_modules.strip().lower() == "all":
                task_builders.print_execution_plan_summary(ctx)
            _plan_modules = task_builders.normalize_execution_modules(_exec_modules, ctx)
            org_phase_ran = "org_provider" in _plan_modules
            print(f"  Modules (ordered): {', '.join(_plan_modules)}")
        else:
            org_phase_ran = task_builders.workflow_runs_org_provider(workflow_mode)
        skip_org_provider = os.getenv("FLOTORCH_SKIP_ORG_PROVIDER", "").strip().lower() in (
            "1", "true", "yes", "y"
        )
        if _exec_config and _exec_config.get("SKIP_ORG_PROVIDER"):
            skip_org_provider = True
        if skip_org_provider:
            print("\n>>> SKIPPING PHASE 2: FLOTORCH_SKIP_ORG_PROVIDER is set <<<\n")
            org_phase_ran = False
        if org_phase_ran:
            print("\n>>> STARTING PHASE 2: Create organization (global) provider <<<\n")
            if not await _ensure_authenticated(llm=llm, browser_session=browser_session, ctx=ctx):
                print("Unable to recover authenticated session before Phase 2.")
                raise RuntimeError("Authentication recovery failed before Phase 2")
            org_history = await _run_agent_phase(
                label="Phase 2: Org provider",
                task=task_builders.build_task_org_provider_phase(ctx),
                llm=llm,
                browser_session=browser_session,
                max_steps=55,
            )
            if org_history.is_successful() is not True:
                if await _ensure_authenticated(llm=llm, browser_session=browser_session, ctx=ctx):
                    print("Retrying Phase 2 once after login recovery...")
                    org_history = await _run_agent_phase(
                        label="Phase 2: Org provider (retry after recovery)",
                        task=task_builders.build_task_org_provider_phase(ctx),
                        llm=llm,
                        browser_session=browser_session,
                        max_steps=55,
                    )
        print("\n>>> STARTING PHASE 3: Workspace create and enter <<<\n")
        if not await _ensure_authenticated(llm=llm, browser_session=browser_session, ctx=ctx):
            print("Unable to recover authenticated session before Phase 3.")
            raise RuntimeError("Authentication recovery failed before Phase 3")
        workspace_history = await _run_agent_phase(
            label="Phase 3: Workspace create and enter",
            task=task_builders.build_task_workspace_phase(ctx, org_phase_ran=org_phase_ran),
            llm=llm,
            browser_session=browser_session,
            max_steps=70,
            watch_workspace_fallback=True,
        )
        if history_mentions_token(workspace_history, WORKSPACE_GATE_FAILED_TOKEN):
            print("\n" + "=" * 50)
            print("WORKSPACE GATE FAILED — skipping remaining workspace phases.")
            print("=" * 50)
        else:
            if _exec_modules is not None:
                phase_specs = task_builders.workspace_phases_from_execution_plan(_exec_modules, ctx)
                print("  Workspace phases:", " → ".join(label for label, _, _, _ in phase_specs))
            else:
                phase_specs = task_builders.workspace_phases_for_workflow_mode(workflow_mode, ctx=ctx)
            for label, builder_name, max_steps, needs_files in phase_specs:
                builder = getattr(task_builders, builder_name)
                if not await _ensure_authenticated(llm=llm, browser_session=browser_session, ctx=ctx):
                    print(f"Unable to recover authenticated session before {label}.")
                    raise RuntimeError(f"Authentication recovery failed before {label}")
                hist = await _run_agent_phase(
                    label=label,
                    task=builder(ctx),
                    llm=llm,
                    browser_session=browser_session,
                    max_steps=max_steps,
                    available_file_paths=(
                        WORKFLOW_AVAILABLE_FILE_PATHS if needs_files else None
                    ),
                )
                extra_phases.append((label, hist))
            if extra_phases:
                close_history = extra_phases[-1][1]

        print("\n" + "=" * 50)
        print("AUTOMATION COMPLETE")
        print("=" * 50)
        if close_history:
            print(
                f"  Suite close: is_done={close_history.is_done()} | "
                f"successful={close_history.is_successful()}"
            )
        print("  (per-phase traces are in the report files below)")

        plan_label = (
            task_builders.execution_plan_label(ctx, _exec_modules)
            if _exec_modules is not None
            else None
        )
        report_kwargs = dict(
            login_history=login_history,
            workflow_history=close_history,
            login_ok=True,
            login_override=login_override,
            workflow_mode=workflow_mode,
            org_history=org_history,
            workspace_history=workspace_history,
            extra_phases=extra_phases or None,
            run_id=ctx.uid,
            workspace_name=ctx.workspace_name,
            plan_label=plan_label,
            report_ctx=ctx,
            execution_modules=_exec_modules,
        )
        report_text = build_scenario_report(**report_kwargs)
        report_html = build_scenario_report_html(**report_kwargs)
        print(report_text)

        out_path, html_path = save_scenario_reports(ctx.uid, report_text, report_html)
        print(f"\nSaved full trace to {out_path}")
        print(f"Saved HTML report to {html_path}")
    finally:
        await close_browser_session(browser_session)


if __name__ == "__main__":
    run_async(main())
