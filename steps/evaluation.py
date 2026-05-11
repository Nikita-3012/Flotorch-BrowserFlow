"""STEP 9–10: LLM and prompt evaluations."""

from run_context import RunContext


def step_llm_evaluation(ctx: RunContext) -> str:
    return f"""
==============================
STEP 9: RUN LLM EVALUATION
==============================
- Skip any optional fields on the form; only complete required fields.
- Go to Evaluations section
- Click "LLM Model Evaluation"
- Provide Name: "llm-evals-evaluation-{ctx.uid}"
- Select model(s) from Step 5 if created else select Global Model for 'Models to evaluate Field
- Select model(s) from Step 6 if created else select Global Model for 'LLM as a Judge' field
- Select embedding model from Step 7 (if created) for 'Eval Embedding Model' field
- Select dataset "llm-evals-{ctx.uid}" from Step 8 for 'Dataset' field
- Click 'Continue' button
- Wait for 'Metrics Selection' Screen to be visible
- Click on 'Select All' button to select all metrics
- Click on 'Next' button
- Wait for 'Review and Run' Screen to be visible
- Click the primary Run control to start the evaluation (label may be "Run", "Run(1)", "Run(2)", or similar — click the matching Run button)
- Wait for success toast/overlay to disappear or is dismissed (close it if needed) so it does not block header clicks.   
- Back to the evaluation list and validate the evaluation is created for "llm-evals-evaluation-{ctx.uid}" in the evaluation search bar and validating it appears in results
"""


def step_prompt_evaluation(ctx: RunContext) -> str:
    return f"""
==============================
STEP 10: RUN PROMPT EVALUATION
==============================
Same overall flow as Step 9 (Configuration → Metrics Selection → Review and Run), but evaluation type is Prompt and you must upload the prompt JSON file.

- Go to Evaluations section
- Click "Prompt Evaluation" (or Create / New evaluation → choose Prompt Evaluation if that is how the UI exposes it)
- On Configuration:
  - Skip every optional field (do not set Vector Storages, KNN, or other optional controls unless the UI blocks Continue).
  - Provide Name: "prompt-evals-evaluation-{ctx.uid}"
  - Dataset: select "llm-evals-{ctx.uid}" from Step 8 (same dataset as LLM eval)
  - Evaluation Type: must be "Prompt". If it shows another type, use "Change" and set it to Prompt
  - N-Shot Prompts: keep default "0" unless the UI requires otherwise
  - Vector Storages / KNN: optional — leave empty; do not create or select vector storage for this automation
  - Models to evaluate: same rule as Step 9 — use workspace/global models from Steps 5–6 if created, else Global Model
  - LLM as a Judge: same rule as Step 9
  - Eval Embedding Model: same as Step 7 embedding model if created, else choose an available embedding-capable model
  - Prompt Pairs: click "Upload JSON" and upload this exact file from the project (repository relative path): Dataset/prompt-without-kb.json
    Do not invent JSON in the UI — use only this file. If the file picker opens elsewhere, navigate to the project folder and select prompt-without-kb.json under the Dataset folder.
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


def final_summary(ctx: RunContext) -> str:
    wsp = ctx.selected_second_provider
    return f"""
==============================
FINAL SUMMARY
==============================
Report:
1. Workspace: "{ctx.workspace_name}" or "Default Workspace" (if fallback) — status
2. Global Provider: "{ctx.org_provider_name}" — status
3. Workspace Provider: "{ctx.workspace_second_provider_name if wsp else 'SKIPPED'}" — status
4. Models: list each model name + provider
5. Embedding model: name + provider (or skipped)
6. Dataset: "llm-evals-{ctx.uid}" — status
7. LLM evaluation ("llm-evals-evaluation-{ctx.uid}") — status
8. Prompt evaluation ("prompt-evals-evaluation-{ctx.uid}") — status
"""
