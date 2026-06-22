"""Playground steps — reusable for different flows (partials, models, guardrails, etc.)."""

from FloTorch.config.run_context import RunContext
from FloTorch.prompts.steps.models import (
    flo_torch_chat_model_names_for_run,
    guardrail_test_model_name,
    prompt_partials_chat_model_name,
)
from FloTorch.prompts.steps.prompt_partials import (
    PARTIAL_V1_DATA_THEME,
    PARTIAL_V2_DATA_THEME,
    playground_probe_query_latest,
    playground_probe_query_v1,
    prompt_partial_name,
)


def _custom_model_name(
    ctx: RunContext,
    *,
    step6_models_created: bool,
    single_chat_model: bool = False,
) -> str | None:
    if not step6_models_created:
        return None
    if single_chat_model:
        name = prompt_partials_chat_model_name(ctx)
        return name or None
    names = flo_torch_chat_model_names_for_run(ctx)
    return names[0] if names else None


def _query1_model_select_block(custom: str | None) -> str:
    if custom:
        return f"""
- Click **FloTorch Models** dropdown.
- **Custom models were created** in this run — select the custom FloTorch pipeline (exact name): `{custom}`
- VERIFY: closed trigger shows `{custom}`.
"""
    return """
- Click **FloTorch Models** dropdown.
- **No custom models** were created in this run — select a **Global Model** (first published global chat option).
- VERIFY: closed trigger shows a global model name.
"""


def step_playground_validate_prompt_partial(
    ctx: RunContext,
    *,
    step6_models_created: bool = False,
    single_chat_model: bool = False,
) -> str:
    name = prompt_partial_name(ctx.uid)
    q1 = playground_probe_query_latest(name)
    q2 = playground_probe_query_v1(name)
    custom = _custom_model_name(
        ctx,
        step6_models_created=step6_models_created,
        single_chat_model=single_chat_model,
    )
    q1_model_block = _query1_model_select_block(custom)
    return f"""
==============================
STEP 6: PLAYGROUND — VALIDATE PROMPT PARTIAL
==============================
PREREQUISITE: Step 5 completed — partial `{name}` exists; v1 data **{PARTIAL_V1_DATA_THEME}**, v2 data **{PARTIAL_V2_DATA_THEME}**; both versions published; latest partial version is **2**.
The prompt partial latest version (2 / {PARTIAL_V2_DATA_THEME}) applies automatically — you do NOT switch the model Version dropdown.

Navigate: Sidebar → **Playground** → **Models** section.

{q1_model_block}
- Do **not** change the Version dropdown — the model has a single Published version; the prompt partial version is resolved through the query syntax `:1` / `:2`, not the model Version dropdown.

**QUERY 1** — type exactly: `{q1}`
- Run and wait for full response.
- PASS if response relates to **{PARTIAL_V2_DATA_THEME}** theme (prompt partial latest version 2 applies automatically).

**QUERY 2** — keep the SAME FloTorch Model as Query 1. Do **not** switch to a different model.
- Clear the input, then type exactly: `{q2}`
- The `:1` in the query references prompt partial version 1 ({PARTIAL_V1_DATA_THEME}).
- Run and wait for full response.
- PASS if response relates to **{PARTIAL_V1_DATA_THEME}** theme.

Report PASS/FAIL per query in memory.
"""


def step_playground_validate_guardrails(ctx: RunContext) -> str:
    model_name = guardrail_test_model_name(ctx.uid)
    if not ctx.has_detected_providers or ctx.first_provider is None:
        return """
==============================
PLAYGROUND — GUARDRAIL SANITY QUERIES
==============================
SKIP — guardrail test model was not created (no .env providers).
"""
    return f"""
==============================
PLAYGROUND — GUARDRAIL SANITY VALIDATION (VERIFY EACH RESPONSE)
==============================
PREREQUISITE: Guardrail test model `{model_name}` with 2 Published revisions:
- Revision 1: Input = Custom Keyword/Replace, Output = AWS Provider/Block
- Revision 2: Input = SS Guardrail/Redact, Output = Phone Guardrail/Log

After **every** query: read the full response (or lack of response) and decide PASS/FAIL against the expected behavior below. Do not mark PASS without checking the actual UI output.

---
**Navigate to Playground**
---
- Sidebar → **Playground** → **Models** section.
- **FloTorch Models**: select **`{model_name}`** (exact).
- Wait for input field and **Version** dropdown.

---
**PHASE 1 — VERSION 1**
---
- **Version**: select **1** (revision 1).
- VERIFY: version trigger shows **1**.

**QUERY 1 — Custom Keyword Replace (input guardrail)**
- Input exactly:
  `What does escalate mean in workplace conflict?`
- Click Run and wait until the response finishes (or validation appears).
- **VERIFY response (required):**
  - **PASS** if the model response is based on the **replaced** keyword **resolve** — e.g. the answer addresses **"What does resolve mean in workplace conflict?"** (or equivalent wording with **resolve**, not **escalate** unchanged in the question context).
  - **FAIL** if the response still treats **escalate** as the active keyword or ignores the replace guardrail.
- Record: "Query 1 Keyword Replace (v1) — PASS/FAIL" with one sentence citing what you saw.

**QUERY 2 — AWS Provider Block (output guardrail)**
- Clear the input field.
- Input exactly:
  `what is racism`
- Click Run and wait for full response.
- **VERIFY response (required):**
  - **PASS** if the answer is otherwise sensible **but** wherever the word **racism** would appear in the output it shows as **`[Redacted]`** (or equivalent redaction token) — the AWS Block guardrail is working.
  - **FAIL** if the raw word **racism** appears unredacted in the model response.
- Record: "Query 2 AWS Block racism (v1) — PASS/FAIL" with one sentence citing what you saw.

---
**PHASE 2 — VERSION latest (revision 2)**
---
- **Version**: switch to **latest published** (revision 2).
- VERIFY: version trigger shows latest (not 1).

**QUERY 3 — SS Guardrail Redact (input guardrail)**
- Clear the input field.
- Input exactly:
  `Grammar check, order 123 45 6789 is my where`
- Click Run and wait.
- **VERIFY response (required):**
  - **PASS** if there is **no normal model answer** — only a **validation popup / toast / message** indicating the guardrail **blocked** or stopped the request (e.g. "guardrail blocked", blocked by guardrail, or similar).
  - **FAIL** if a full chat response is returned as if the guardrail did not intervene.
- Record: "Query 3 SS Redact (v2) — PASS/FAIL" with one sentence citing what you saw.

**QUERY 4 — Phone Guardrail Log (output guardrail)**
- Clear the input field.
- Input exactly:
  `my is where order +919876543210. grammatically correct`
- Click Run and wait for full response.
- **VERIFY response (required):**
  - **PASS** if you receive a **normal, coherent grammatical correction** (or similar helpful answer) based on the query — the **Log** action does **not** block or redact; the phone number may appear and the answer should address grammar/word order.
  - **FAIL** if the request is blocked with only a guardrail popup and no answer, or if the response is empty when a normal answer was expected.
- Record: "Query 4 Phone Log (v2) — PASS/FAIL" with one sentence citing what you saw.

---
**Finalize**
---
- **Overall PASS** only if all 4 queries pass their verification above.
- Report each query with PASS/FAIL and a short evidence line from the UI.
- Use **done** with success=true only if all four passed; otherwise success=false.
"""


def playground_guardrails_final_summary(ctx: RunContext) -> str:
    model_name = guardrail_test_model_name(ctx.uid)
    lines = [
        f"1. Guardrail test model `{model_name}` (2 revisions published) — PASS/FAIL",
        "2. Playground → Models navigation — PASS/FAIL",
        "3. Query 1 (v1): Replace — response reflects resolve/workplace question — PASS/FAIL",
        "4. Query 2 (v1): AWS Block — racism shows [Redacted] in output — PASS/FAIL",
        "5. Query 3 (v2): SS Redact — guardrail popup, no normal response — PASS/FAIL",
        "6. Query 4 (v2): Phone Log — normal grammatical answer, log does not block — PASS/FAIL",
        "7. Overall guardrail Playground sanity — PASS/FAIL",
    ]
    return f"""
==============================
FINAL SUMMARY (GUARDRAIL PLAYGROUND)
==============================
Report each line with PASS or FAIL:

{chr(10).join(lines)}
"""


def playground_final_summary(
    ctx: RunContext,
    *,
    step6_models_created: bool = False,
    single_chat_model: bool = False,
) -> str:
    name = prompt_partial_name(ctx.uid)
    q1 = playground_probe_query_latest(name)
    q2 = playground_probe_query_v1(name)
    custom = _custom_model_name(
        ctx,
        step6_models_created=step6_models_created,
        single_chat_model=single_chat_model,
    )
    model_label = f"custom `{custom}`" if custom else "Global Model"
    return f"""
==============================
FINAL SUMMARY (PLAYGROUND)
==============================
Report each line ending with " — PASS" or " — FAIL" (replace PASS/FAIL with your verdict):

7. Playground → Models, RAG, Workflows visible — PASS
8. Models screen loaded — PASS
9. Query 1 ({q1}) | {model_label} | v2 theme {PARTIAL_V2_DATA_THEME} — PASS
10. Query 2 ({q2}) | {model_label} (same model, :1 for v1) | v1 theme {PARTIAL_V1_DATA_THEME} — PASS
11. Overall Playground validation — PASS
"""
