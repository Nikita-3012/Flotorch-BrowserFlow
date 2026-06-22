"""STEP 5: Second LLM provider inside the workspace."""

from FloTorch.config.run_context import RunContext
from FloTorch.prompts.steps.provider_form_rules import provider_service_and_type_select_all


def build_workspace_provider_text(ctx: RunContext) -> str:
    if not ctx.has_detected_providers:
        return "- SKIP — no provider credentials in FloTorch/.env; Step 2 was skipped. Go to the next step."
    sp = ctx.selected_second_provider
    if not sp:
        return "- SKIP — only 1 provider available in .env. Go to model creation."
    return f"""
- Click on 'Model Registry' 
- Click on 'Providers' tab
- Click 'Add LLM Provider' button

Inside the modal:
- In the "Name" field:
   Enter exactly (all lowercase, use hyphens between words — no spaces): {ctx.workspace_second_provider_name}

- In the "Description" field:
   Enter exactly: {ctx.workspace_second_provider_description}

- In the "Provider" dropdown (Reka/Radix combobox — read the REKA section of the system message first):
   - Click the Provider dropdown trigger to open the popper. Wait ~500ms for options to render.
   - **PRIMARY (deterministic, 1-attempt selection): use the evaluate JS template from the REKA section with `want = "{sp['name']}"`.** This matches the exact label "{sp['name']}" (not a prefix), so it cannot pick a similarly-named provider by mistake (e.g. it won't pick "Google Vertex AI" when you want "Google Generative AI"). The template dispatches the full pointer+mouse event sequence — plain `.click()` does NOT work on Radix.
   - **FALLBACK (only if PRIMARY returns 'no-match' or 'no-options-found'):** keyboard typeahead — but be careful: typing one letter (e.g. "G") may highlight the wrong sibling. Use ArrowDown until the highlighted row's visible label is exactly "{sp['name']}", then press Enter.
   - **DO NOT** spam click(index) on the option — Radix ignores plain index-clicks.
   - VERIFICATION (single, simple check):
       (B) the popper wrapper `[data-reka-popper-content-wrapper]` is gone (Reka auto-closes on selection — no manual close needed).
       (C) the trigger now displays exactly "{sp['name']}".
      If (B) and (C) are both true → the provider IS selected, proceed.
      If only (B) is true but trigger is empty → reopen and use the OTHER strategy (if typeahead failed, use JS fallback; if JS failed, use typeahead).
      If (B) is false (popper still open) → the option click missed entirely; retry once.
    - DO NOT look for a "checkmark while the list is open" — Reka closes the popper on selection, so the tick is invisible by the time you'd observe it. Trust the trigger text.
    - Maximum 2 selection attempts. If still not selected after 2 attempts, accept partial failure and continue.
   - HARD GATE: do not type the API Key or any credential until (B) and (C) are both true.

- After selecting the provider type, additional credential fields will appear

{provider_service_and_type_select_all()}

- Fill provider credential fields using ONLY the values from {sp['fields']}

Rules:
- Before typing each credential, re-check the closed Provider trigger still shows exactly "{sp['name']}". If it does not, fix provider first — never type secrets into Name/Description.
- For each credential field shown in the UI, match its label with the exact key in {sp['fields']}
- Scroll **inside** the modal body: use the scrollable **inner column** that contains the form fields (not only the outer dialog frame). Scroll until the credential label (e.g. "API Key") is on-screen before clicking it.
- Before typing, click the **label text** "API Key" (or the matching credential label) or its dedicated input so focus is NOT in Name or Description. If the typed characters appear in Description, you clicked the wrong element — stop, click the correct field, clear, and type again.
- If unsure which field is focused, click the credential label/input again, then type.
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
