"""Prompt Partials smoke test (Prompts → Partials → New Prompt Partial)."""

from FloTorch.config.run_context import RunContext


def prompt_partial_name(uid: str) -> str:
    return f"tech-{uid}"


PARTIAL_V1_DATA_THEME = "IOT"
PARTIAL_V2_DATA_THEME = "AI Agent"


def playground_validation_query(uid: str) -> str:
    """Legacy / alternate probe (long form). Prefer playground_probe_query_latest / playground_probe_query_v1."""
    return (
        f"Automation check for run {uid}: respond in one short sentence and mention "
        f"whether {PARTIAL_V1_DATA_THEME} and {PARTIAL_V2_DATA_THEME} context from the prompt partial should influence your answer."
    )


def playground_probe_query_latest(name: str) -> str:
    """Query 1 — latest partial (expect response related to version 2 / {PARTIAL_V2_DATA_THEME})."""
    return "What is {{" + name + "}}"


def playground_probe_query_v1(name: str) -> str:
    """Query 2 — partial version 1 (expect response related to version 1 / {PARTIAL_V1_DATA_THEME})."""
    return "What is {{" + name + ":1" + "}}"


def step_prompt_partials(ctx: RunContext) -> str:
    name = prompt_partial_name(ctx.uid)
    description = f"Technology prompt partial configuration - {ctx.uid}"
    data = PARTIAL_V1_DATA_THEME
    data2 = PARTIAL_V2_DATA_THEME
    return f"""
==============================
STEP 5: PROMPT PARTIALS — NEW PARTIAL
==============================
PREREQUISITE: Already inside workspace "{ctx.workspace_name}" (Step 4 complete).

Navigation:
- In the left sidebar, open the **Prompts** menu/section.
- Click the **Partials** submenu item under Prompts.
- Wait for the Partials page to finish loading (list or empty state visible).

Open new partial:
- Click **New Prompt Partial** button
- Wait for the create form or modal to render.

If a Name field is shown and required:
- Name (exact, lowercase, hyphens between words — no spaces): `{name}`
- Provide Description for the partial: `{description}`
- Provide Data for the Partial: `{data}`
- Click on 'Create' button
- wait for the success toast to appear and disappear
- Search and validate the new partial is listed in the Partials page with the name `{name}`
- Click the **three dots (⋯)** in the Actions column for partial `{name}` → **Versions**.
- Wait for the Versions page to load.

**Publish Version 1 (initial version — data `{data}`):**
- In the versions table, find the row for the **first / initial** version (content matches `{data}`, or the only row present before you create another version).
- Open **Actions** on that row → **Publish**.
- Wait for the success toast to appear and fully dismiss (close it if it blocks UI).
- Confirm that row shows status **Published** (badge or column text).

**Create Version 2:**
- Click **New Version**.
- Wait for the form to render.
- Set **Data** for this version to: `{data2}`
- Click **Create**.
- Wait for the success toast to appear and disappear.
- Confirm a **second** row appears and its data matches `{data2}`.

**Publish Version 2 (data `{data2}`):**
- Find the row for the version whose data is `{data2}` (not the initial `{data}` row).
- Open **Actions** on that row → **Publish**.
- Wait for the success toast to appear and disappear.
- Confirm that row shows status **Published**.

**Final check:**
- Exactly **two** versions are listed for partial `{name}`.
- **Both** rows show status **Published** (initial `{data}` and new `{data2}`).

- Click on back button to go to the Partials page
- Search and validate the new partial is listed in the Partials page with the name `{name}`
- Click the **three dots (⋯)** in the Actions column for partial `{name}` → **Publish Latest**.
- Wait for Publish Latest modal to appear
- Click on the 'Dropdown' button and select the '2(Pubished)' option
- Click on the 'Publish' button
- wait for the success toast to appear and disappear
- Wait for the Versions page to load
- Wait for the 'Latest Version' column to show '2'


Verification (required before continuing):
- Prompts → Partials → Versions navigation succeeded.
- Partial `{name}` exists on the Partials list after creation.
- Both versions published as above.
"""


def partials_final_summary(ctx: RunContext) -> str:
    return f"""
==============================
FINAL SUMMARY
==============================
Report:
1. Workspace: "{ctx.workspace_name}" or "Default Workspace" (if fallback) — status
2. Prompts → Partials navigation — status
3. New Prompt Partial form/modal opened — status
4. Partial name: "tech-{ctx.uid}" — status
5. Version 1 (data: IOT) — Published — status
6. Version 2 (data: AI Agent) — Published — status
"""
