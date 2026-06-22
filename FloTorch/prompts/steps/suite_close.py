"""End-of-suite: agent closes the test run."""

from FloTorch.config.run_context import RunContext
from FloTorch.prompts.steps.evaluation import evaluations_final_summary, final_summary


def step_suite_close(ctx: RunContext) -> str:
    return f"""
==============================
SUITE CLOSE — END OF AUTOMATION
==============================
All prior phases should be complete (org provider, workspace, models, vector, datasets, evaluations, prompt partials).

{final_summary(ctx)}

TERMINATION (MANDATORY):
- Review the checklist above; note PASS/FAIL/SKIP for each area in your done message.
- Call the "done" tool with success=true (unless a blocking failure prevents closing the suite).
- Do not start new creates, evaluations, or navigation — this phase only closes the test run.
"""


def step_suite_close_evaluations(ctx: RunContext) -> str:
    return f"""
==============================
SUITE CLOSE — END OF AUTOMATION (evaluations suite)
==============================
All prior phases should be complete (workspace provider, models, vector if configured, datasets, evaluations).

{evaluations_final_summary(ctx)}

TERMINATION (MANDATORY):
- Review the checklist above; note PASS/FAIL/SKIP for each area in your done message.
- Call the "done" tool with success=true (unless a blocking failure prevents closing the suite).
- Do not start new creates, evaluations, or navigation — this phase only closes the test run.
"""
