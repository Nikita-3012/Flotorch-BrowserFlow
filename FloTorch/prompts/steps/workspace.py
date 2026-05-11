"""STEP 3–4: Create workspace and enter it."""

from FloTorch.config.constants import WORKSPACE_FALLBACK_TOKEN
from FloTorch.config.run_context import RunContext


def step_create_and_enter_workspace(ctx: RunContext) -> str:
    return f"""
==============================
STEP 3: CREATE WORKSPACE
==============================
Primary path:
- Go to Workspace screen
- Click Create / New Workspace
- Name: {ctx.workspace_name}
- Description: workspace created by automation run {ctx.uid}
- Save and confirm

Failure handling (if create fails, name rejected, quota error, validation error, or workspace does not appear):
- Do not abandon the suite.
- Search or browse the workspace list for an existing workspace named exactly: Default Workspace
- Open that workspace (click it) so you are inside it for later steps.
- On the very next model step after you commit to this fallback, include the exact token {WORKSPACE_FALLBACK_TOKEN} in your "memory" field (required for automation logging).


==============================
STEP 4: ENTER WORKSPACE
==============================
- If Step 3 primary path succeeded: click "{ctx.workspace_name}" to open it (use search if many workspaces).
- If Step 3 used the failure path: you should already be inside Default Workspace — if not, open "Default Workspace" from the list.
- Wait for the workspace shell to finish loading before Step 5.
"""
