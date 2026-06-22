"""STEP 6–7: Chat models and embedding model."""

from FloTorch.config.name_slug import name_field_slug
from FloTorch.config.run_context import RunContext
from FloTorch.prompts.steps.guardrails import (
    pipeline_base_model_from_env,
    sanity_aws_provider_guardrail_block_name,
    sanity_custom_keyword_replace_name,
    sanity_final_io_guardrail_names_bullets,
)


def _model_select_instruction(ctx: RunContext) -> str:
    if ctx.model_name:
        return f"""Select the model named **"{ctx.model_name}"** from the **in-app model dropdown** on the FloTorch console (Model Registry pipeline). Search/typeahead if the list is long; scroll until you see the exact name. **"{ctx.model_name}"** is a vendor model id — do NOT navigate the browser to it as a URL (e.g. never open https://amazon.nova). Do NOT pick the first model unless it matches "{ctx.model_name}"."""
    return """Select the **first model** in that dropdown list (topmost/first visible option — index 0). Do not scroll past or pick a random model."""


def _model_select_instruction_short(ctx: RunContext) -> str:
    if ctx.model_name:
        return f"""Select **"{ctx.model_name}"** in the pipeline model dropdown only (not a URL — never navigate to amazon.nova or similar)"""
    return """Select the **first model** in the list (topmost option)"""


def _pipeline_configure_and_publish_steps(ctx: RunContext) -> str:
    model_sel = _model_select_instruction(ctx)
    return f"""
PIPELINE UI — perform this full sequence for EACH chat model defined above (complete one model fully before starting the next):
  1. Open Model Registry, then go to the Models section (Models under Model Registry).
  2. Click "Create FloTorch Model".
  3. In the modal: enter Name and Description exactly as specified for this model in the list above (Name must be lowercase with hyphens between words — no spaces). Keep Type as "Chat". If Create/Save is off-screen, scroll down inside the modal, then submit.
  4. Wait a few seconds until the pipeline builder screen loads (Draft badge; columns such as Input Guardrails, Router, Models & Cache, Output Guardrails — pipeline configuration layout).
  5. In the Models column, click the "+" (plus) icon in the Models row/header area.
  6. **Provider then model (strict order):**
     a) Select the workspace/global provider instance (PROVIDER DROPDOWN RULE below). Wait until provider trigger shows the correct instance name.
     b) Open the **model / base model** dropdown (appears after provider is set).
     c) {model_sel}
     d) Click "Save Configuration".
  6.5. **VERIFY SAVE BEFORE TOUCHING PUBLISH (deterministic — the most common publish-bug cause):** after clicking Save Configuration, wait 2 seconds, then run THIS JS to check Publish button state:
     `(() => {{ const btn = document.querySelector('button[aria-label="Publish Model"]'); if (!btn) return 'no-publish-button-yet'; return btn.disabled || btn.hasAttribute('disabled') || btn.getAttribute('aria-disabled')==='true' ? 'publish-disabled' : 'publish-enabled'; }})()`
      - `publish-enabled` → save succeeded, proceed to step 7.
      - `publish-disabled` or `no-publish-button-yet` → wait 2 more seconds and re-check once more.
   7. ONLY after publish-enabled: trigger the Publish button via the PUBLISH MODEL JS in the system message (deterministic dispatch). DO NOT use a plain index-click — index-clicks have been observed to register as the button click but fail to open the dialog. The system message gives you the exact JS to use.
      - After the JS returns `clicked`, wait 2 seconds.
      - Then run the dialog-detection JS from the system message. If it returns `{{open: true, ...}}`, proceed to step 8. The dialog IS present even if your screenshot looks unchanged — Reka teleports it. Trust the JS, not the screenshot.
      - If `{{open: false}}`: re-click Save Configuration first (state may have reset), then retry Publish once.
  8. Once the publish dialog is open (per the dialog-detection JS): set the Summary to the exact underlying model name you chose from the dropdown (the vendor/base model identifier — not the FloTorch pipeline name from step 3).
  9. Check the option "Mark as latest version once published".
  10. Click the Publish button INSIDE the dialog to confirm. After clicking, the dialog should close on its own within 2-3 seconds.
  11. **HARD VERIFICATION of publish (do not skip):** wait up to 10 seconds for ONE of these signals:
     a) A toast/popup containing "Model Version Published", "Published successfully", "Version published", or similar.
     b) The pipeline screen's status badge changes from "Draft" to "Published".
     c) The browser navigates back to `/registry/models` AND the model row for this pipeline shows a "Published" status indicator (not "Draft").
      If NONE of (a)/(b)/(c) is visible after 10 seconds, the publish did NOT complete — click the inner Publish button once more. Do not proceed to the next model until publish is verified.

After model 1 is fully done (including the published popup), repeat steps 1–11 for the next model in the list using its Name, Description, and correct provider.
"""


def _pipeline_configure_single_model_steps(ctx: RunContext) -> str:
    model_sel = _model_select_instruction(ctx)
    return f"""
PIPELINE UI — perform this sequence **once** for the single chat model defined above:
  1. Open Model Registry, then go to the Models section (Models under Model Registry).
  2. Click "Create FloTorch Model".
  3. In the modal: enter Name and Description exactly as specified above (Name must be lowercase with hyphens between words — no spaces). Keep Type as "Chat". If Create/Save is off-screen, scroll down inside the modal, then submit.
  4. Wait a few seconds until the pipeline builder screen loads (Draft badge; columns such as Input Guardrails, Router, Models & Cache, Output Guardrails — pipeline configuration layout).
  5. In the Models column, click the "+" (plus) icon in the Models row/header area.
  6. **Provider then model (strict order):**
     a) Select the organization provider instance (PROVIDER DROPDOWN RULE below). Wait until provider trigger shows the correct instance name.
     b) Open the **model / base model** dropdown (appears after provider is set).
     c) {model_sel}
     d) Click "Save Configuration".
  6.5. **VERIFY SAVE BEFORE PUBLISH:** after Save Configuration, wait 2 seconds, then run the publish-button JS from the system message (`publish-enabled` required).
  7. Publish via PUBLISH MODEL JS (not plain index-click). Complete dialog: Summary = underlying base model name; check **Mark as latest**; confirm inner Publish.
  8. **HARD VERIFICATION:** toast "Model Version Published" / Published badge / registry row shows Published — do not continue until verified.
  9. Do **not** create a second FloTorch chat model in this phase.
"""


def _provider_dropdown_rule(*, model1_want: str, model2_want: str | None = None, ctx: RunContext | None = None) -> str:
    second_line = ""
    if model2_want:
        second_line = f"""
  - For Model 2, select the workspace provider instance created in Step 5 (exact): "{model2_want}"
    Do NOT select a generic vendor type name (e.g. "Google Generative AI") — only this instance name."""
    model_rule = _model_select_instruction_short(ctx) if ctx and ctx.model_name else "always pick the **first** model in the model dropdown list unless the task explicitly names another model"
    select_gate = f"""Select {ctx.model_name}""" if ctx and ctx.model_name else "provider + first model"
    return f"""
PROVIDER DROPDOWN RULE (pipeline Models column — Reka/Radix, see REKA section):
  - For Model 1, select the organization provider instance created in Step 2 (exact): "{model1_want}"
    Do NOT select the vendor type name (e.g. "Groq", "Google Generative AI") — only the custom Name you created in Step 2.
{second_line}
  - PRIMARY: click the trigger, wait ~500ms, run the REKA evaluate JS with `want` set to that exact instance name above.
  - FALLBACK if PRIMARY returns 'no-match': keyboard typeahead + ArrowDown until the highlighted row matches exactly.
  - VERIFY: after the popper closes, the trigger text must show the instance name above. If not, retry once.
  - HARD GATE: do not open the model dropdown until the provider trigger shows the correct instance name.
  - After provider is set, {model_rule}.
  - HARD GATE: do not click Save Configuration until {select_gate} are both selected.
  - Do not start the next model until publish is verified for the current model."""


def _provider_dropdown_rule_single(*, provider_want: str, ctx: RunContext | None = None) -> str:
    """Provider rule for suites that create exactly one chat pipeline."""
    model_sel = _model_select_instruction_short(ctx) if ctx and ctx.model_name else "Pick the **first** base model in the list"
    return f"""
PROVIDER DROPDOWN RULE (pipeline Models column — Reka/Radix, see REKA section):
  - Select the organization provider instance created in Step 2 (exact): "{provider_want}"
    Do NOT select the vendor type name (e.g. "Groq", "Google Generative AI") — only the custom Name you created in Step 2.
  - PRIMARY: click the trigger, wait ~500ms, run the REKA evaluate JS with `want` set to that exact instance name.
  - VERIFY: after the popper closes, the trigger text must show "{provider_want}".
  - HARD GATE: do not open the base model dropdown until the provider trigger is correct.
  - {model_sel}, then Save Configuration.
  - This suite creates **only one** FloTorch model — do not create `{provider_want}` chat pipelines with other names.
"""


def _model_select_text(ctx: RunContext, *, label: str) -> str:
    if ctx.model_name:
        return f"select the model named **\"{ctx.model_name}\"** from the provider dropdown"
    return f"pick the first available base model"


def build_chat_models_text(ctx: RunContext) -> str:
    first = ctx.first_provider
    if first is None:
        raise RuntimeError("build_chat_models_text called without a detected provider")
    second = ctx.selected_second_provider
    uid = ctx.uid
    desc = f"model created for automation run-{uid}"
    org_provider = ctx.org_provider_name
    model_sel_m1 = _model_select_text(ctx, label="Model 1")
    if second:
        slug1 = name_field_slug(first["name"])
        slug2 = name_field_slug(second["name"])
        name_first = f"{slug1}-{uid}"
        name_second = f"{slug2}-{uid}"
        ws_provider = ctx.workspace_second_provider_name or ""
        return f"""
You have 2 providers. Create 1 model from each provider (2 models total):
  - Model 1: organization provider "{org_provider}" (Step 2, type {first['name']}) — {model_sel_m1}
    - Name (exact, lowercase, hyphens between words — no spaces): {name_first}
    - Description (exact): {desc}
  - Model 2: workspace provider "{ws_provider}" (Step 5, type {second['name']}) — pick the first available base model
    - Name (exact, lowercase, hyphens between words — no spaces): {name_second}
    - Description (exact): {desc}

{_provider_dropdown_rule(model1_want=org_provider, model2_want=ws_provider, ctx=ctx)}

{_pipeline_configure_and_publish_steps(ctx)}"""
    slug = name_field_slug(first["name"])
    name_one = f"{slug}-{uid}"
    name_two = f"{slug}-{uid}-2"
    return f"""
You have 1 provider. Create 2 different models from organization provider "{org_provider}" (Step 2, type {first['name']}):
  - Model 1: {model_sel_m1}
    - Name (exact, lowercase, hyphens between words — no spaces): {name_one}
    - Description (exact): {desc}
  - Model 2: pick a DIFFERENT base model from the same provider instance
    - Name (exact, lowercase, hyphens between words — no spaces): {name_two}  (suffix "-2" distinguishes the second model)
    - Description (exact): {desc}

{_provider_dropdown_rule(model1_want=org_provider, model2_want=org_provider, ctx=ctx)}

{_pipeline_configure_and_publish_steps(ctx)}"""


def prompt_partials_chat_model_name(ctx: RunContext) -> str:
    """Single chat pipeline name for FLOTORCH_WORKFLOW=prompt_partials."""
    if not ctx.has_detected_providers or ctx.first_provider is None:
        return ""
    slug = name_field_slug(ctx.first_provider["name"])
    return f"{slug}-{ctx.uid}"


def build_single_chat_model_text(ctx: RunContext) -> str:
    """One org-provider chat model — prompt partials suite only."""
    first = ctx.first_provider
    if first is None:
        raise RuntimeError("build_single_chat_model_text called without a detected provider")
    uid = ctx.uid
    desc = f"model created for automation run-{uid}"
    org_provider = ctx.org_provider_name
    name = prompt_partials_chat_model_name(ctx)
    model_sel = _model_select_text(ctx, label="Model")
    return f"""
Create **exactly one** FloTorch chat model for Prompt Partials + Playground (do **not** create a second model):
  - Organization provider "{org_provider}" (Step 2, type {first['name']})
  - {model_sel}
  - Name (exact, lowercase, hyphens between words — no spaces): {name}
  - Description (exact): {desc}

{_provider_dropdown_rule(model1_want=org_provider, ctx=ctx)}

{_pipeline_configure_single_model_steps(ctx)}"""


def guardrail_test_model_name(uid: str) -> str:
    return f"guardrail-test-{uid}"


def _guardrail_test_pipeline_steps(*, guardrail_names_bullets: str, org_provider: str) -> str:
    return f"""
PIPELINE UI — **one** guardrail test model (complete fully before Playground):
  1. Open Model Registry → **Models** section.
  2. Click **Create FloTorch Model**.
  3. Modal: enter Name and Description exactly as specified below (lowercase, hyphens — no spaces). Type **Chat**. Scroll modal if needed; submit Create.
  4. Wait until pipeline builder loads (Draft badge; **Input Guardrails**, Router, **Models & Cache**, Output Guardrails columns visible).

  5. **INPUT GUARDRAILS** (before Models column):
     a) In the **Input Guardrails** column/section, click the **+** (plus) icon.
     b) Wait for guardrail picker/list (search or checklist).
     c) Attach **every** custom guardrail created in this run (**8** total — Keyword×4 + Regex×4). Select each by exact name; use search if available. If **Select All** exists and selects only this run's guardrails, you may use it.
     d) Guardrails to attach (all required):
{guardrail_names_bullets}
     e) Confirm all **8** names appear as attached/selected on the pipeline before continuing.
     f) Save/apply guardrail selection if the UI requires a separate confirm button.

  6. **Models & Cache** column: click **+** in the Models row/header area.
  7. **Provider then model (strict order):**
     a) Select organization provider instance (exact): "{org_provider}"
     b) Open **model / base model** dropdown after provider is set.
     c) Select the **first** model in the list (topmost option).
     d) Click **Save Configuration**.
  8. **VERIFY SAVE BEFORE PUBLISH:** wait 2s, run publish-button JS from system message (`publish-enabled` required).
  9. Publish via PUBLISH MODEL JS (not plain index-click). Complete dialog: Summary = underlying base model name; check **Mark as latest**; confirm inner Publish.
  10. **HARD VERIFICATION:** toast "Model Version Published" / Published badge / registry row shows Published — do not continue until verified.
  11. Stop — do **not** create a second FloTorch chat model in this suite.
"""


def flo_torch_chat_model_names_for_run(ctx: RunContext) -> list[str]:
    """FloTorch chat pipeline names Step 6 would create (same naming as build_chat_models_text).
    Empty list when Step 6 would SKIP (no providers in .env)."""
    if not ctx.has_detected_providers or ctx.first_provider is None:
        return []
    first = ctx.first_provider
    uid = ctx.uid
    second = ctx.selected_second_provider
    if second:
        slug1 = name_field_slug(first["name"])
        slug2 = name_field_slug(second["name"])
        return [f"{slug1}-{uid}", f"{slug2}-{uid}"]
    slug = name_field_slug(first["name"])
    return [f"{slug}-{uid}", f"{slug}-{uid}-2"]


def build_embedding_text(ctx: RunContext) -> str:
    if not ctx.has_detected_providers:
        return "SKIP — no providers from FloTorch/.env; do not create an embedding model."
    ep = ctx.embedding_provider
    if not ep:
        return "SKIP — no detected providers support embedding."
    return f"""
Create 1 embedding model from "{ep['name']}" (supports embeddings):
  - Navigate to Models section under the 'Model Registry' Menu
  - Click "Create FloTorch Model"
  - Name (exact, lowercase, hyphens between words — no spaces): v1-embedding-{ctx.uid}
  - Description: embedding model for automation run {ctx.uid}
  - Click on 'Type' Dropdown and select the Embedding Optionss
  - Open the Embedding provider Dropdown and select the any available Provider
  - Select any Available Embedding Models
  - Create on Create Button and verify the validation success message
  - Search in the List and verify Embedding models created or nots
"""


def step_chat_models(ctx: RunContext) -> str:
    if not ctx.has_detected_providers or ctx.first_provider is None:
        return """
==============================
STEP 6: CREATE MODELS
==============================
SKIP — models are only created when FloTorch/.env supplies at least one complete provider credential set (same condition as creating providers in Steps 2 and 5).
No providers were detected from .env for this run, so do not create FloTorch chat models; continue to the next step.
"""
    model_text = build_chat_models_text(ctx)
    return f"""
==============================
STEP 6: CREATE MODELS
==============================
{model_text}
- Follow the PIPELINE UI sequence in order for each model; do not skip Publish or the "Model Version Published" confirmation.
- Provider selection must use exact provider name text (from .env), not list position.
"""


def step_chat_model_for_prompt_partials(ctx: RunContext) -> str:
    if not ctx.has_detected_providers or ctx.first_provider is None:
        return """
==============================
STEP 6: CREATE ONE CHAT MODEL (PROMPT PARTIALS SUITE)
==============================
SKIP — no providers in FloTorch/.env; Playground will use a Global Model in the next phase.
"""
    model_text = build_single_chat_model_text(ctx)
    return f"""
==============================
STEP 6: CREATE ONE CHAT MODEL (PROMPT PARTIALS SUITE)
==============================
{model_text}
- Create **only one** Published chat pipeline — required for Playground in the next phase.
- Provider selection must use exact org provider instance name from Step 2, not list position.
"""


def step_guardrail_test_model(ctx: RunContext) -> str:
    if not ctx.has_detected_providers or ctx.first_provider is None:
        return """
==============================
GUARDRAIL TEST MODEL
==============================
SKIP — no providers in FloTorch/.env; cannot create guardrail test pipeline. Continue to next step only if Playground can use another model.
"""
    org_provider = ctx.org_provider_name
    model_name = guardrail_test_model_name(ctx.uid)
    desc = f"guardrail sanity model for run {ctx.uid}"
    replace_name = sanity_custom_keyword_replace_name(ctx.uid)
    aws_block_name = sanity_aws_provider_guardrail_block_name(ctx.uid)
    final_io_bullets = sanity_final_io_guardrail_names_bullets(ctx)
    base_model_sel = pipeline_base_model_from_env(ctx)
    return f"""
==============================
GUARDRAIL TEST MODEL — ONE MODEL ONLY (GUARDRAILS SUITE)
==============================
PREREQUISITE: Guardrails sanity create phase completed (4 guardrails created).
Org provider: **{ctx.org_provider_name}** (created in Phase 2 — do NOT create a new provider).

**FLOTORCH_WORKFLOW=guardrails:** create **only** this model (`{model_name}`).
Do **not** run the standard Step 6 flow (no second chat model, no `-2` suffix model, no embedding model).
Do **not** create any organization providers, workspace providers, or datasets.

Model creation sequence:

--- REVISION 1 ---
1) Create model and configure guardrails:
   a) Click **Create FloTorch Model**. Name: `{model_name}`, Description: `{desc}`, Type: Chat.
   b) Wait for pipeline builder (Draft badge; Input Guardrails, Router, Models & Cache, Output Guardrails columns).
   c) **Input Guardrails** column: click **+** and attach exactly ONE guardrail:
      - `{replace_name}` (Custom Keyword, action Replace)
   d) **Output Guardrails** column: click **+** and attach exactly ONE guardrail:
      - `{aws_block_name}` (AWS Provider Guardrail, action Block) — skip if Bedrock guardrail was not created
   e) **Models & Cache** column: click **+** → select organization provider `{org_provider}` → {base_model_sel} → Save Configuration.
   f) VERIFY SAVE → Publish revision 1 (toast "Model Version Published" / Published badge).

--- REVISION 2 ---
2) Click **Make a revision** and update guardrail placement:
   a) **Input Guardrails**: remove existing, then click **+** and attach exactly ONE:
{final_io_bullets.split(chr(10))[0]}
   b) **Output Guardrails**: remove existing, then click **+** and attach exactly ONE:
{final_io_bullets.split(chr(10))[1]}
   c) Save Configuration and Publish revision 2.

Model metadata:
  - Name (exact): `{model_name}`
  - Description (exact): `{desc}`
  - Organization provider: "{org_provider}" ({ctx.first_provider['name'] if ctx.first_provider else 'N/A'})
  - Base model: {base_model_sel}

{_provider_dropdown_rule_single(provider_want=org_provider, ctx=ctx)}

BASE MODEL RULE (guardrails suite):
- {base_model_sel}
- HARD GATE: do not click **Save Configuration** until the model dropdown shows the .env model name exactly.
- **Never** use `navigate` to open the base model string as a URL.

RULES:
- **Exactly one** Published pipeline for this suite: `{model_name}` with 2 revisions.
- Publish revision 1 and revision 2 successfully before moving to Playground.
- Playground must select `{model_name}` only.
"""


def step_embedding_model(ctx: RunContext) -> str:
    embedding_text = build_embedding_text(ctx)
    return f"""
==============================
STEP 7: CREATE EMBEDDING MODEL
==============================
{embedding_text}
"""
