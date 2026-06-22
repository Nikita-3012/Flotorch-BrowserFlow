"""STEP 9: Vector storage repositories — Add Vector Storage flow with table/embedding dropdowns."""

from FloTorch.config.run_context import RunContext
from FloTorch.prompts.steps.provider_form_rules import provider_service_and_type_select_all


def _repo_table_instruction(path: dict, *, is_dropdown: bool) -> str:
    repo = path.get("repository") or {}
    table = repo.get("table_name", "")
    if not table:
        return "Table / Index: leave default or select first available option."
    if is_dropdown:
        return f"Table / Index dropdown: select exactly **{table}**."
    return f"Table / Index text input: type exactly **{table}**."


def _repo_embedding_instruction(path: dict, uid: str) -> str:
    """Always select the FloTorch embedding pipeline (v1-embedding-{uid}), not the vendor model ID."""
    return f"Embedding model dropdown: select **v1-embedding-{uid}** (the FloTorch embedding pipeline created in Step 7)."


def step_vector_repositories(ctx: RunContext) -> str:
    if not ctx.has_vector_rag_path or not ctx.vector_active_path:
        return """
==============================
STEP 9: VECTOR STORAGE REPOSITORIES
==============================
SKIP — no vector storage path active. Continue to datasets.
"""

    path = ctx.vector_active_path

    # For org reuse: fallback job may have the provider instance name
    if ctx.vector_providers_planned and path.get("use_org_provider"):
        job = ctx.vector_providers_planned[0]
        path = {**job, **path}
    elif ctx.vector_providers_planned:
        path = {**ctx.vector_providers_planned[0], **path}

    repo = path.get("repository") or {}
    repo_name = path.get("repository_name", "")
    is_dd = repo.get("table_is_dropdown", "true") == "true"
    table_instruction = _repo_table_instruction(path, is_dropdown=is_dd)
    emb_instruction = _repo_embedding_instruction(path, uid=ctx.uid)

    provider_ref = path.get("provider_ref", "")

    # Determine where the provider comes from
    if path.get("use_org_provider"):
        org_type = path.get("org_provider_type", "")
        provider_hint = f"""
**Provider for this repository:** `{provider_ref}` — this is the org-level **{org_type}** provider created in Step 2.
It should be available under workspace Vector Storage (verified in Step 8).
"""
    else:
        provider_hint = f"""
**Provider for this repository:** `{provider_ref}` — this is the vector storage provider created in Step 8.
"""

    return f"""
==============================
STEP 9: VECTOR STORAGE REPOSITORY (one only)
==============================
{provider_hint}
Create **one** repository for the active vector path.

### ADD VECTOR STORAGE FLOW:

1. Navigate to workspace-level **Vector Storage** section.
2. Click **"Add Vector Storage"** button (or equivalent create button).
3. Wait for the **Add new vector storage** popup / modal to be visible.
4. Fill the form fields:
   - **Name** (exact, lowercase, hyphens between words — no spaces): {repo_name}
   - **Description**: repository for automation run {ctx.uid}
   - **Provider / Vector Storage dropdown**: select exactly **{provider_ref}**
{provider_service_and_type_select_all()}
5. **{table_instruction}**
6. **{emb_instruction}**
7. If there is a **Create** button at the bottom of the modal, scroll down inside the modal to make it visible, then click **Create**.
8. Close the modal if needed; verify **"{repo_name}"** appears in the repository list.
9. If the repository row is visible with status, confirm creation succeeded.

Do **NOT** create repositories for other vector DB types not used in this run.
"""
