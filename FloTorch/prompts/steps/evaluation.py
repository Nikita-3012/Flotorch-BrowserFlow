"""STEP 9–10: LLM and prompt evaluations."""

from pathlib import Path

from FloTorch.config.run_context import RunContext
from FloTorch.prompts.steps.models import flo_torch_chat_model_names_for_run

_FLOTORCH_ROOT = Path(__file__).resolve().parent.parent.parent


def _eval_prioritize_step6_chat_models(
    ctx: RunContext, *, nested_under_configuration: bool = False
) -> str:
    """Prefer FloTorch chat pipelines from Step 6; else Global Model (aligned with Playground)."""
    names = flo_torch_chat_model_names_for_run(ctx)
    if not names:
        raw = """- **Models to evaluate** and **LLM as a Judge**: Step 6 did not create chat pipelines this run — select **Global Model** (or any offered global chat model) for each field."""
    else:
        bullets = "\n".join(
            f"  - Prefer **`{n}`** (FloTorch chat pipeline from Step 6; must be **Published**)."
            for n in names
        )
        raw = f"""- **Models to evaluate** / **LLM as a Judge**:
  - When Step 6 ran, prefer these pipeline names if they appear in each dropdown and are **Published**:
{bullets}
  - Use **different** Step 6 pipelines for the two roles when the UI requires two distinct models; if only one exists, use Global for the second role when needed.
  - If **none** of the names above appear or are not selectable: select **Global Model** for that field instead."""
    if nested_under_configuration:
        return "\n".join(f"  {line}" if line.strip() else "" for line in raw.splitlines())
    return raw


def prompt_pairs_path() -> str:
    return str((_FLOTORCH_ROOT / "Dataset" / "prompt-without-kb.json").resolve())


def step_llm_evaluation(ctx: RunContext) -> str:
    return f"""
==============================
STEP 12: RUN LLM EVALUATION
==============================
**FLOTORCH_WORKFLOW=evaluations or full:** run after datasets exist.
Uses the single dataset created in Step 11 ("llm-evals-{ctx.uid}").
- Skip any optional fields on the form; only complete required fields.
- Go to Evaluations section
- Click "LLM Model Evaluation"
- Provide Name (lowercase, hyphens between words — no spaces): "llm-evals-evaluation-{ctx.uid}"
{_eval_prioritize_step6_chat_models(ctx)}
- **Eval Embedding Model**: Step 7 if created (`v1-embedding-{ctx.uid}`), else any available embedding-capable model
- Select dataset "llm-evals-{ctx.uid}" from Step 11
- Click 'Continue' button
- Wait for 'Metrics Selection' Screen to be visible
- Click on 'Select All' button to select all metrics
- Click on 'Next' button
- Wait for 'Review and Run' Screen to be visible
- Click the primary Run control to start the evaluation (label may be "Run", "Run(1)", "Run(2)", or similar — click the matching Run button)
- Wait for success toast/overlay to disappear or is dismissed (close it if needed) so it does not block header clicks.   
- Return to the evaluation list and validate "llm-evals-evaluation-{ctx.uid}" appears in list.
"""


def step_prompt_evaluation(ctx: RunContext) -> str:
    prompt_json = prompt_pairs_path()
    chat_model_rules = _eval_prioritize_step6_chat_models(
        ctx, nested_under_configuration=True
    )
    return f"""
==============================
STEP 13: RUN PROMPT EVALUATION
==============================
Same overall flow as Step 9 (Configuration → Metrics Selection → Review and Run), but evaluation type is Prompt and you must upload the prompt JSON file.
Do NOT go to Datasets or create another dataset — reuse "llm-evals-{ctx.uid}" from Step 11.

- Go to Evaluations section
- Click "Prompt Evaluation" (or Create / New evaluation → choose Prompt Evaluation if that is how the UI exposes it)
- On Configuration:
  - Skip every optional field (do not set Vector Storages, KNN, or other optional controls unless the UI blocks Continue).
  - Provide Name (lowercase, hyphens between words — no spaces): "prompt-evals-evaluation-{ctx.uid}"
  - Dataset: select "llm-evals-{ctx.uid}" from Step 11 (same dataset as LLM evaluation)
  - Evaluation Type: must be "Prompt". If it shows another type, use "Change" and set it to Prompt
  - N-Shot Prompts: keep default "0" unless the UI requires otherwise
  - Vector Storages / KNN: optional — leave empty; do not create or select vector storage for this automation
{chat_model_rules}
  - **Eval Embedding Model**: Step 7 if created (`v1-embedding-{ctx.uid}`), else choose an available embedding-capable model
  - Prompt Pairs: click "Upload JSON" and upload this exact file (do not invent JSON in the UI):
    {prompt_json}
  - Verify the uploaded file name or prompt pairs preview appears before Continue
- Click 'Continue' button
- Wait for 'Metrics Selection' screen
- Click 'Select All' for metrics (or select required metrics if Select All is absent)
- Click 'Next' button
- Wait for 'Review and Run' screen
- Click the primary Run control (label may be "Run", "Run(1)", "Run(2)", or similar)
- Wait for success toast/overlay to dismiss if it blocks UI
- Return to evaluation list and validate "prompt-evals-evaluation-{ctx.uid}" appears in search results
"""


def evaluations_final_summary(ctx: RunContext) -> str:
    """Checklist for FLOTORCH_WORKFLOW=evaluations (focused suite)."""
    wsp = ctx.selected_second_provider
    vector_lines = ""
    if ctx.vector_providers_skipped:
        vector_lines += "\nVector skip notes:\n" + "\n".join(
            f"  - {s}" for s in ctx.vector_providers_skipped
        )
    if ctx.vector_active_path:
        p = ctx.vector_active_path
        vector_lines += (
            f"\nVector RAG path: {p.get('provider_ref', 'N/A')} "
            f"(org reuse={p.get('use_org_provider', False)})"
        )
    return f"""
==============================
FINAL SUMMARY (evaluations suite)
==============================
Report:
1. Workspace: "{ctx.workspace_name}" or "Default Workspace" (if fallback) — status
2. Global Provider ({ctx.org_provider_type or 'SKIPPED'}): "{ctx.org_provider_name or 'SKIPPED'}" — status
3. Workspace Provider: "{ctx.workspace_second_provider_name if wsp else 'SKIPPED'}" — status
4. Chat models (Step 6) — status
5. Embedding model: v1-embedding-{ctx.uid} (or skipped) — status
6. Vector storage providers — status{vector_lines}
7. Vector repositories — status
8. RAG datasets — status
9. LLM dataset ("llm-evals-{ctx.uid}") — status
10. LLM evaluation ("llm-evals-evaluation-{ctx.uid}") — status
11. Prompt evaluation ("prompt-evals-evaluation-{ctx.uid}") — status
12. RAG evaluation(s) — status (SKIP if no vector path in .env)
13. Suite close — status
"""


def final_summary(ctx: RunContext) -> str:
    wsp = ctx.selected_second_provider
    vector_lines = ""
    if ctx.vector_providers_skipped:
        vector_lines += "\nVector skip notes:\n" + "\n".join(
            f"  - {s}" for s in ctx.vector_providers_skipped
        )
    if ctx.vector_active_path:
        p = ctx.vector_active_path
        vector_lines += (
            f"\nVector RAG path: {p.get('provider_ref', 'N/A')} "
            f"(org reuse={p.get('use_org_provider', False)})"
        )
        if ctx.org_verify_sections:
            vector_lines += "\nOrg verify sections: " + ", ".join(ctx.org_verify_sections)
    guardrail = (
        "available"
        if ctx.guardrail_tests_available
        else "SKIP (no Amazon Bedrock in .env)"
    )
    return f"""
==============================
FINAL SUMMARY
==============================
Report:
1. Workspace: "{ctx.workspace_name}" or "Default Workspace" (if fallback) — status
2. Global Provider ({ctx.org_provider_type or 'SKIPPED'}): "{ctx.org_provider_name or 'SKIPPED'}" — status
3. Amazon Bedrock guardrail scenarios: {guardrail}
4. Workspace Provider: "{ctx.workspace_second_provider_name if wsp else 'SKIPPED'}" — status
5. Chat models: list each model name + provider — status
6. Embedding model: v1-embedding-{ctx.uid} (or skipped) — status
7. Vector storage providers — status{vector_lines}
8. Vector repositories — status
9. RAG datasets — status
10. LLM dataset ("llm-evals-{ctx.uid}") — status
11. LLM evaluation ("llm-evals-evaluation-{ctx.uid}") — status
12. Prompt evaluation ("prompt-evals-evaluation-{ctx.uid}") — status
13. RAG evaluations (per vector path) — status
14. Guardrails regression (Custom×8 + AWS×3 + SS×4 + Phone×4) + guardrail-test model + Playground — status
15. Prompt Partials + Playground — status
16. Suite close — status
"""
