"""STEP 2: Create organization (global) provider."""

from FloTorch.config.run_context import RunContext
from FloTorch.prompts.steps.provider_form_rules import provider_service_and_type_select_all


def _org_post_create_verification(ctx: RunContext) -> str:
    if not ctx.org_verify_sections or not ctx.org_provider_name:
        return ""
    sections = "\n".join(f"  - **{s}**" for s in ctx.org_verify_sections)
    bedrock_extra = ""
    if ctx.org_provider_type == "Amazon Bedrock":
        bedrock_extra = """
- Bedrock org provider must appear in **Guardrails provider** — if missing, report FAIL for guardrails linkage.
"""
    return f"""
==============================
VERIFY ORG PROVIDER IN WORKSPACE SECTIONS (mandatory after create)
==============================
Org provider instance name to search (exact): **{ctx.org_provider_name}**
Org vendor type: **{ctx.org_provider_type}**

For each section below, open Model Registry → Providers (or org Providers area), switch to that tab/section, use search for `{ctx.org_provider_name}`, and confirm the row appears.

Sections to verify:
{sections}
{bedrock_extra}
- **PASS** each section where the provider row is listed.
- **FAIL** and note the section name if search returns no row.
- Do **not** create duplicate Bedrock/OpenAI providers in Vector storage or Guardrails — org provider should already appear there when linkage works.
- Include verification results (PASS/FAIL per section) in memory before calling done.
"""


def step_org_provider(ctx: RunContext) -> str:
    if not ctx.has_detected_providers or ctx.first_provider is None:
        return """
==============================
STEP 2: CREATE GLOBAL PROVIDER
==============================
SKIP — no LLM provider credentials were detected in FloTorch/.env (no complete credential set for any registered provider).
Global providers are only created when .env includes the required keys for at least one provider.
Do not open Create Organization Provider for this run; continue to the next step.
"""
    fp = ctx.first_provider
    guardrail_note = ""
    if ctx.org_provider_skip_note:
        guardrail_note = f"""
REPORT NOTE (include in memory when Step 2 ends):
- {ctx.org_provider_skip_note}
"""
    priority_note = f"""
SELECTION PRIORITY FOR THIS RUN (always checked in this order):
  1. Amazon Bedrock — used if Bedrock credentials (Access Key, Secret Key, Region) are configured in .env
  2. OpenAI — used if Bedrock is not configured but OpenAI API Key is present in .env
  3. First available provider — fallback when neither Bedrock nor OpenAI is configured

This run selected: **{fp['name']}** as the organization provider.
"""
    return f"""
==============================
STEP 2: CREATE GLOBAL PROVIDER
==============================
{priority_note}
{guardrail_note}
CRITICAL — CREATE EXACTLY ONE PROVIDER:
- Create ONLY the provider specified below ({fp['name']}).
- Do NOT create any other provider types (Groq, Google Generative AI, Google Vertex AI, OpenAI, etc.).
- Do NOT navigate to other provider sections or create duplicate providers.
- After creating this single provider, proceed directly to the next step.

- Go to Provider section (organization / global scope — not inside a workspace).
- Click Create Organization Provider

Inside the modal:
- In the "Name" field:
   Enter exactly (all lowercase, use hyphens between words — no spaces): {ctx.org_provider_name}

- In the "Description" field:
   Enter (all lowercase): {ctx.org_provider_description}

- In the "Provider" dropdown:
   - Click the Provider dropdown first. Wait ~1s after the overlay opens.
   - **SCROLL INSIDE THE DROPDOWN OVERLAY** until "{fp['name']}" is fully visible.
   - Select ONLY: {fp['name']}
   - Verify checkmark/tick on "{fp['name']}" before closing Provider list.
   - Close Provider dropdown (trigger or neutral space inside modal).

{provider_service_and_type_select_all()}

- After Service dropdown is fully closed, fill credentials from config only:

Field mappings:
- "API Key" → {fp['fields'].get('API Key', '')}
- "Base URL" → {fp['fields'].get('Base URL', '')}
- "Region" → {fp['fields'].get('Region', '')}
- "Access Key" → {fp['fields'].get('Access Key', '')}
- "Secret Key" → {fp['fields'].get('Secret Key', '')}
- "Project ID" → {fp['fields'].get('Project ID', '')}
- "Service Account" → {fp['fields'].get('Service Account', '')}
- "Private Key" → {fp['fields'].get('Private Key', '')}

- Scroll modal; click "Create Provider"
- Search `{ctx.org_provider_name}` in org provider list — must appear.
- STOP — do NOT create any additional providers after this one.

{_org_post_create_verification(ctx)}
"""
