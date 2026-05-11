import asyncio
import sys

from browser_use import Agent, ChatGoogle
from browser_use.browser import BrowserSession

# Make sure stdout can print Unicode box-drawing chars used by the scenario table.
# On Windows, the default console codepage (cp1252) can't encode `─│┌┐` etc.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass

from FloTorch.runtime.logging_utils import make_step_end_logger
from FloTorch.config.providers import build_run_context
from FloTorch.reporting.report_mail import maybe_send_report_email
from FloTorch.reporting.scenario_report import build_scenario_report, build_scenario_report_html
from FloTorch.prompts.tasks import build_task_login, build_task_workflow


async def main():
    ctx = build_run_context()
    if not ctx.email or not ctx.password:
        print("ERROR: FLOTORCH_EMAIL and FLOTORCH_PASSWORD must be set in the environment.")
        raise SystemExit(1)

    task_login = build_task_login(ctx)
    task_workflow = build_task_workflow(ctx)

    llm = ChatGoogle(model="gemini-2.5-flash")

    # 75% zoom: 1920x1080 window renders 2560x1440 worth of content
    # Modals that were cut off will now fit completely on screen
    # keep_alive=True: first Agent.run() must NOT call kill() on this session, or the next Agent
    # can hit "BrowserStateRequestEvent ... none did" (event bus / DOM watchdog out of sync). We kill in `finally` below.
    browser_session = BrowserSession(
        headless=False,
        keep_alive=True,
        window_size={"width": 1920, "height": 1080},
        args=["--force-device-scale-factor=0.75", "--start-maximized"],
    )

    print(f"\nWorkspace: {ctx.workspace_name}")
    print(f"Global Provider (name field): {ctx.org_provider_name}")
    print(
        f"Workspace Provider: {ctx.selected_second_provider['name'] if ctx.selected_second_provider else 'N/A'}"
    )
    print(f"Embedding: {ctx.embedding_provider['name'] if ctx.embedding_provider else 'N/A'}")
    print("Browser: 1920x1080 @ 75% zoom (effective 2560x1440)")
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

            definitely_still_on_login = (
                "/auth/signin" in current_url
                or "/auth/login" in current_url
                or current_url.endswith("/auth")
            )
            if current_url and not definitely_still_on_login:
                print("\n" + "=" * 50)
                print("LOGIN OVERRIDE: Agent reported failure, but browser appears authenticated.")
                print(f"Current URL after TC-01: {current_url}")
                print("Continuing with Steps 2–10.")
                print("=" * 50)
                login_ok = True
                login_override = True

        if not login_ok:
            print("\n" + "=" * 50)
            print("SUITE ABORTED: TC-01 LOGIN did not pass — skipping all downstream steps.")
            print("Fix credentials or account state, then re-run.")
            print("=" * 50)
            out_path = f"result-{ctx.uid}.txt"
            html_path = f"result-{ctx.uid}.html"
            report_text = build_scenario_report(
                login_history=login_history,
                workflow_history=None,
                login_ok=False,
                login_override=False,
            )
            report_html = build_scenario_report_html(
                run_id=ctx.uid,
                login_history=login_history,
                workflow_history=None,
                login_ok=False,
                login_override=False,
            )
            print(report_text)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(report_text)
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(report_html)
            print(f"\nSaved login-phase trace to {out_path}")
            print(f"Saved HTML report to {html_path}")
            maybe_send_report_email(out_path, run_id=ctx.uid, html_body=report_html)
            return

        # --- Phase 2: full workflow (same browser session) ---
        print("\nPhase 2: post-login QA workflow (Steps 2–10)\n")
        workflow_agent = Agent(
            task=task_workflow,
            llm=llm,
            browser_session=browser_session,
            max_actions_per_step=5,
            use_vision=True,
        )
        result = await workflow_agent.run(
            max_steps=200,
            on_step_end=make_step_end_logger("WORKFLOW", watch_workspace_fallback=True),
        )

        print("\n" + "=" * 50)
        print("AUTOMATION COMPLETE")
        print("=" * 50)
        print(result)

        report_text = build_scenario_report(
            login_history=login_history,
            workflow_history=result,
            login_ok=True,
            login_override=login_override,
        )
        report_html = build_scenario_report_html(
            run_id=ctx.uid,
            login_history=login_history,
            workflow_history=result,
            login_ok=True,
            login_override=login_override,
        )
        print(report_text)

        out_path = f"result-{ctx.uid}.txt"
        html_path = f"result-{ctx.uid}.html"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(report_text)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(report_html)
        print(f"\nSaved full trace to {out_path}")
        print(f"Saved HTML report to {html_path}")
        maybe_send_report_email(out_path, run_id=ctx.uid, html_body=report_html)
    finally:
        try:
            await browser_session.kill()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())
