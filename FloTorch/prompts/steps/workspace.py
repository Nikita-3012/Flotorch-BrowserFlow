"""STEP 3–4: Create workspace and enter it."""

from FloTorch.config.constants import WORKSPACE_FALLBACK_TOKEN, WORKSPACE_GATE_FAILED_TOKEN
from FloTorch.config.run_context import RunContext


def step_create_and_enter_workspace(ctx: RunContext) -> str:
    uid = ctx.uid
    ws = ctx.workspace_name
    return f"""
==============================
STEP 3: CREATE WORKSPACE
==============================
This run **always creates a new workspace** — never reuse a name from a prior run.

Go to the **Workspaces** screen.
Click **Create** / **New Workspace**.
In the modal, set fields EXACTLY (copy character-for-character from this prompt):
  - **Name** (lowercase, hyphens between words — no spaces): {ws}
  - **Description**: workspace created by automation run {uid}
Click **Create** and wait until the modal closes and the list refreshes (toast or new row visible).
Do not open any workspace row until that refresh is done.

**HARD RULE — use this run's uid only:**
- This run's uid is: **{uid}**
- Workspace name must be: **{ws}** (= `automation-` + uid)
- Do **not** search for or open any other `automation-…` row from older runs.

Failure handling (only if create fails, name rejected, quota error, validation error, or workspace does not appear):
Do not abandon the suite.
Search or browse the workspace list for an existing workspace named exactly: **Default Workspace**
Open that workspace (click it) so you are inside it for later steps.
On the very next model step after you commit to this fallback, include the exact token {WORKSPACE_FALLBACK_TOKEN} in your "memory" field (required for automation logging).

==============================
STEP 4: ENTER WORKSPACE
==============================
WHY WRONG ROWS GET CLICKED: many `automation-…` workspaces exist from past runs; truncated UI labels look identical.
**This run must open:** `{ws}` (suffix `{uid}` only — not any other uid).

If Step 3 primary path succeeded:
  1. Paste the **full** name into the workspace search box: `{ws}`
  2. Wait **2 seconds** for the table to filter/update.
  3. **Do NOT** index-click the first visible `automation-…` link.
  4. **PRIMARY (deterministic):** use the WORKSPACE LIST evaluate JS from the system message with `uid = '{uid}'` to click the row whose link text contains that suffix.
  5. **VERIFY:** run the workspace verify JS with `uid = '{uid}'` — must return `workspace-ok`. If `workspace-wrong` or `no-match`, go back to the list and retry once.
  6. Only after verify passes: continue to the next step.

If Step 3 used the failure path: you should already be inside Default Workspace — if not, open "Default Workspace" from the list.
Wait for the workspace shell to finish loading before continuing.

If you CANNOT enter Default Workspace (not listed, click fails, or workspace shell never loads):
- Put exact token {WORKSPACE_GATE_FAILED_TOKEN} in your memory field.
- Finish with done success=false.
- Do NOT run downstream workspace-scoped steps.
- In the final message list all workspace-scoped modules as FAILED.
"""
