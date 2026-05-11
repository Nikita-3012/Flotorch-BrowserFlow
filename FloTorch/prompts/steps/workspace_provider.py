"""STEP 5: Second LLM provider inside the workspace."""

from run_context import RunContext


def build_workspace_provider_text(ctx: RunContext) -> str:
    sp = ctx.selected_second_provider
    if not sp:
        return "- SKIP — only 1 provider available. Go to model creation."
    return f"""
- Click on 'Model Registry' 
- Click on 'Providers' tab
- Click 'Add LLM Provider' button

Inside the modal:
- In the "Name" field:
   Enter exactly (all lowercase): {ctx.workspace_second_provider_name}

- In the "Description" field:
   Enter exactly: {ctx.workspace_second_provider_description}

- In the "Provider" dropdown:
   - Click the Provider dropdown first
   - Click/select ONLY the exact text match: {sp['name']}
   - NEVER choose by position/index (e.g., do not choose "2nd option")
   - Do NOT use arrow keys + Enter to choose an item by position
   - Assume NO search is available; scroll the dropdown list until "{sp['name']}" is visible.
   - Click the exact TITLE row "{sp['name']}" (not the description/subtext line).
   - After clicking the option, CLOSE the dropdown by clicking an empty area inside the modal (preferred).
     Use Escape ONLY if clicking outside does not close it.
   - HARD VERIFICATION (MANDATORY):
       1) The dropdown menu MUST be closed (no list visible)
       2) The combobox field MUST display exactly: "{sp['name']}"
     If either condition is not true, reopen the dropdown and try again (up to 3 attempts) until it sticks.
   - HARD GATE: do not enter API Key or any credentials until the combobox shows exactly "{sp['name']}"

- After selecting the provider type, additional credential fields will appear

- Fill provider credential fields using ONLY the values from {sp['fields']}

Rules:
- Before typing each credential, re-check Provider field still equals "{sp['name']}". If it changed, fix provider first.
- For each credential field shown in the UI, match its label with the exact key in {sp['fields']}
- Before typing, click directly into the specific credential input by its LABEL (e.g., click the "API Key" input).
  Never type credentials into the Name/Description fields by accident.
- If unsure which field is focused, click the label/input again, then type.
- Enter the corresponding value from {sp['fields']} into that field
- Never type placeholder/example values like "test-api-key", "your-api-key", or sample URLs
- Always use the real fetched configuration values

Field mappings:
- "API Key" field → {sp['fields'].get('API Key', '')}
- "Base URL" field → {sp['fields'].get('Base URL', '')}
- "Region" field → {sp['fields'].get('Region', '')}
- "Project ID" field → {sp['fields'].get('Project ID', '')}
- "Service Account" field → {sp['fields'].get('Service Account', '')}
- "Private Key" field → {sp['fields'].get('Private Key', '')}

- SCROLL DOWN inside the modal/dialog if Save/Create button is not visible
- Save and confirm"""


def step_workspace_provider(ctx: RunContext) -> str:
    ws_provider_text = build_workspace_provider_text(ctx)
    return f"""
==============================
STEP 5: CREATE 2ND PROVIDER IN WORKSPACE
==============================
{ws_provider_text}
"""


__all__ = ["build_workspace_provider_text", "step_workspace_provider"]
