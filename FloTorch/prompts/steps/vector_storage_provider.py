"""STEP 8: Vector storage provider — org reuse check, OpenAI embedding, or direct create."""

from FloTorch.config.run_context import RunContext
from FloTorch.prompts.steps.provider_form_rules import provider_service_and_type_select_all


def _credential_block(fields: dict) -> str:
    lines = []
    for k, v in fields.items():
        if v:
            lines.append(f'  - "{k}" → use value from config')
    return "\n".join(lines) if lines else "  - fill required credential fields from UI"


def _openai_workspace_provider_block(ctx: RunContext) -> str:
    """Create OpenAI workspace provider + embedding model before vector storage."""
    path = ctx.vector_active_path or {}
    ws_name = path.get("openai_workspace_provider_name", f"openai-{ctx.uid}")
    ws_desc = path.get("openai_workspace_provider_desc", "")
    emb_model = path.get("openai_embedding_model", "text-embedding-3-small")
    return f"""
--- FIRST: CREATE OPENAI WORKSPACE PROVIDER (required for embedding) ---
Do NOT start vector storage creation until these sub-steps complete.

1. Navigate to Model Registry → Providers.
2. Click "Add LLM Provider" (workspace-level).
3. In the modal:
   - Name (exact, lowercase, hyphens between words — no spaces): {ws_name}
   - Description (exact): {ws_desc}
   - Provider dropdown: select **OpenAI** (the vendor type, not an instance name).
   - Service dropdown: tick **every** Service option (Select All).
   - API Key: use config value for OPENAI_API_KEY.
4. Click Create / Save.
5. Verify "{ws_name}" appears in workspace provider list.

--- SECOND: CREATE EMBEDDING MODEL WITH OPENAI ---
1. Navigate to Model Registry → Models.
2. Click "Create FloTorch Model".
3. Name (exact, lowercase, hyphens between words — no spaces): v1-embedding-{ctx.uid}
4. Description: embedding model for automation run {ctx.uid}
5. Type dropdown: select **Embedding**.
6. Provider dropdown: select "{ws_name}" (the OpenAI workspace provider just created).
7. Model dropdown: select **{emb_model}**.
8. Click Create / Save.
9. Verify "v1-embedding-{ctx.uid}" appears in model list with Published / Active status.

--- NOW PROCEED TO VECTOR STORAGE PROVIDER BELOW ---
"""


def step_vector_storage_providers(ctx: RunContext) -> str:
    path = ctx.vector_active_path

    # ── No vector path at all ──
    if not path and not ctx.vector_providers_planned:
        skip_notes = "\n".join(f"- {s}" for s in ctx.vector_providers_skipped) if ctx.vector_providers_skipped else ""
        return f"""
==============================
STEP 8: VECTOR STORAGE PROVIDERS
==============================
SKIP — no vector path for this run.
{skip_notes}
Continue to LLM dataset step.
"""

    skip_block = ""
    if ctx.vector_providers_skipped:
        skip_block = "NOTES:\n" + "\n".join(f"- {line}" for line in ctx.vector_providers_skipped) + "\n"

    # ── Case A: Org provider is Amazon Bedrock — check Vector Storage, reuse if visible ──
    if path and path.get("use_org_provider") and path.get("org_provider_type") == "Amazon Bedrock":
        org_name = path.get("org_provider_name", "")
        fallback = path.get("fallback_job")
        fallback_block = ""
        if fallback:
            fallback_block = f"""
IF org provider **{org_name}** is NOT found in Vector storage provider section:
- Create **one** fallback vector storage:
  - Type: {fallback['name']}
  - Name: {fallback['provider_instance_name']}
  - Provider dropdown: select {fallback['name']}
  - Credentials:
{_credential_block(fallback['fields'])}
- Verify created vector storage appears in list.
"""
        else:
            fallback_block = """
IF org provider is NOT found in Vector storage section and no fallback vector credentials in .env → report SKIP.
"""
        return f"""
==============================
STEP 8: VECTOR STORAGE — AMAZON BEDROCK ORG REUSE
==============================
{skip_block}
Org provider `{org_name}` (Amazon Bedrock) was created at org level.

1. Navigate to workspace-level **Vector storage provider** section.
2. Search for `{org_name}` in the vector storage provider list.
3. **If {org_name} IS found in Vector storage section:**
   - Do **NOT** create any new vector storage.
   - Report: "Amazon Bedrock org provider visible in workspace Vector Storage — reusing for RAG."
   - SKIP directly to Step 9 (Repository).
4. **If {org_name} is NOT found:**
   - Report: "Amazon Bedrock org provider not visible in workspace Vector Storage."
{fallback_block}
"""

    # ── Case B: Org provider is OpenAI — check Vector Storage, reuse if visible ──
    if path and path.get("use_org_provider") and path.get("org_provider_type") == "OpenAI":
        org_name = path.get("org_provider_name", "")
        fallback = path.get("fallback_job")
        fallback_block = ""
        if fallback:
            fallback_block = f"""
IF org provider **{org_name}** is NOT found in Vector storage provider section:
- Create **one** fallback vector storage:
  - Type: {fallback['name']}
  - Name: {fallback['provider_instance_name']}
  - Provider dropdown: select {fallback['name']}
  - Credentials:
{_credential_block(fallback['fields'])}
- Verify created vector storage appears in list.
"""
        else:
            fallback_block = """
IF org provider is NOT found in Vector storage section and no fallback vector credentials in .env → report SKIP.
"""
        return f"""
==============================
STEP 8: VECTOR STORAGE — OPENAI ORG REUSE
==============================
{skip_block}
Org provider `{org_name}` (OpenAI) was created at org level.

1. Navigate to workspace-level **Vector storage provider** section.
2. Search for `{org_name}` in the vector storage provider list.
3. **If {org_name} IS found in Vector storage section:**
   - Do **NOT** create any new vector storage.
   - Report: "OpenAI org provider visible in workspace Vector Storage — reusing for RAG."
   - SKIP directly to Step 9 (Repository).
4. **If {org_name} is NOT found:**
   - Report: "OpenAI org provider not visible in workspace Vector Storage."
{fallback_block}
"""

    # ── No active path but planned fallback ──
    if not path and ctx.vector_providers_planned:
        job = ctx.vector_providers_planned[0]
        return f"""
==============================
STEP 8: VECTOR STORAGE PROVIDER (single fallback)
==============================
{skip_block}
- Name: {job['provider_instance_name']}
- Provider: {job['name']}
{provider_service_and_type_select_all()}
- Credentials:
{_credential_block(job['fields'])}
- Verify listed after Save.
"""

    # ── Case C / D: Non Bedrock/OpenAI org — create first available vector DB ──
    if path and not path.get("use_org_provider"):
        job = ctx.vector_providers_planned[0] if ctx.vector_providers_planned else path
        job_name = job.get("name", "")
        instance_name = job.get("provider_instance_name", "")
        fields = job.get("fields", {})

        # ── Case D: Needs OpenAI embedding (Pinecone, Chroma, LanceDB, pg-vector) ──
        if path.get("needs_openai_embedding"):
            if path.get("needs_openai_workspace_provider"):
                return f"""
==============================
STEP 8: VECTOR STORAGE — NEED OPEN AI PROVIDER + EMBEDDING FIRST
==============================
{skip_block}
Org provider is **not** Amazon Bedrock or OpenAI. First available vector DB: **{job_name}**.

{job_name} requires an OpenAI embedding model for repository creation.

{_openai_workspace_provider_block(ctx)}

--- THIRD: CREATE VECTOR STORAGE PROVIDER ({job_name}) ---
1. Navigate to **Vector storage provider** section.
2. Click "Add Vector Storage" (or equivalent create button).
3. Wait for the Add new vector storage popup to be visible.
4. Fill the form:
   - Name (exact, lowercase, hyphens between words — no spaces): {instance_name}
   - Description: vector storage for automation run {ctx.uid}
   - Provider dropdown: select **{job_name}**
{provider_service_and_type_select_all()}
   - Credentials:
{_credential_block(fields)}
5. Click Create / Save.
6. Verify "{instance_name}" appears in vector storage provider list.
"""
            else:
                return f"""
==============================
STEP 8: VECTOR STORAGE ({job_name}) — NO OPENAI CREDENTIALS
==============================
{skip_block}
Cannot create {job_name} vector storage — OpenAI credentials not in .env (required for embedding).
SKIP — continue to next step.
"""

        # ── Case C: Azure AI Search (no OpenAI needed) ──
        return f"""
==============================
STEP 8: VECTOR STORAGE PROVIDER — {job_name}
==============================
{skip_block}
Org provider is **not** Amazon Bedrock or OpenAI. First available vector DB: **{job_name}**.

Azure AI Search does not require an OpenAI embedding model — create vector storage directly:

1. Navigate to **Vector storage provider** section.
2. Click "Add Vector Storage" (or equivalent create button).
3. Wait for the Add new vector storage popup to be visible.
4. Fill the form:
   - Name (exact, lowercase, hyphens between words — no spaces): {instance_name}
   - Description: vector storage for automation run {ctx.uid}
   - Provider dropdown: select **{job_name}**
{provider_service_and_type_select_all()}
   - Credentials:
{_credential_block(fields)}
5. Click Create / Save.
6. Verify "{instance_name}" appears in vector storage provider list.
"""

    return """
==============================
STEP 8: VECTOR STORAGE PROVIDERS
==============================
SKIP — nothing to verify or create.
"""
