"""Agent task prompts: login and phased post-login workflow.

Suite execution order (enforced by ``main.py``):
  1. TC-01 Login — hard gate; on FAIL the runner aborts and marks all downstream cases FAIL.
  2. Org provider (global) — precondition: login PASS.
  3. Workspace create + enter — precondition: login PASS (+ org provider in full mode).
  4+ Workspace-scoped steps — precondition: inside a workspace (custom or Default).
"""

from FloTorch.config.run_context import RunContext
from FloTorch.prompts.steps.agent_eval_shared import step_agent_dataset
from FloTorch.prompts.steps.agent_evaluation import step_agent_evaluation
from FloTorch.prompts.steps.workflow_evaluation import step_workflow_evaluation
from FloTorch.prompts.steps.dataset import step_dataset
from FloTorch.prompts.steps.evaluation import step_llm_evaluation, step_prompt_evaluation
from FloTorch.prompts.steps.guardrails import step_guardrails_sanity_create
from FloTorch.prompts.steps.models import (
    guardrail_test_model_name,
    step_chat_model_for_prompt_partials,
    step_chat_models,
    step_embedding_model,
    step_guardrail_test_model,
)
from FloTorch.prompts.steps.org_provider import step_org_provider
from FloTorch.prompts.steps.playground import (
    playground_final_summary,
    playground_guardrails_final_summary,
    step_playground_validate_guardrails,
    step_playground_validate_prompt_partial,
)
from FloTorch.prompts.steps.prompt_partials import partials_final_summary, step_prompt_partials
from FloTorch.prompts.steps.provider_form_rules import provider_service_and_type_select_all
from FloTorch.prompts.steps.rag_dataset import step_rag_datasets
from FloTorch.prompts.steps.rag_evaluation import step_rag_evaluations
from FloTorch.prompts.steps.suite_close import step_suite_close, step_suite_close_evaluations
from FloTorch.prompts.steps.vector_repository import step_vector_repositories
from FloTorch.prompts.steps.vector_storage_provider import step_vector_storage_providers
from FloTorch.prompts.steps.workspace import step_create_and_enter_workspace
from FloTorch.prompts.steps.workspace_provider import step_workspace_provider

_LOGIN_PASS = "TC-01 Login completed successfully (authenticated console, not on /auth/signin)."

_INSIDE_WORKSPACE = (
    "You are inside a FloTorch workspace (custom or Default Workspace). "
    f"Preconditions satisfied: {_LOGIN_PASS} Org provider step completed (or SKIPped). "
    "Workspace create and enter completed."
)


def build_task_login(ctx: RunContext) -> str:
    return f"""
You execute exactly ONE test case — Phase 1 of the suite. Do not start any other QA steps after login.
The runner will not execute org provider, workspace, models, datasets, or evaluations unless this case PASSES.

EXECUTION RULES (SPEED + RELIABILITY):
- Do NOT use write_file/replace_file or maintain todo.md in this task.
- Do NOT use search_page for auth error detection (it can match hidden/script text and cause false failures).
- Determine PASS/FAIL only from visible UI + current URL.
- If URL leaves /auth/signin (or dashboard/admin shell is visible), treat login as PASS.
- If still on login, wait once (3-5s) and re-check before declaring FAIL.

---
TEST CASE ID: TC-01
TITLE: FloTorch Console — user authentication
PRIORITY: P0 (blocking — downstream tests must not run if this fails)
TYPE: Functional / smoke

PRECONDITIONS:
- Valid network access to https://console.flotorch.cloud/
- Test credentials are supplied below (do not ask the user for them).

TEST DATA:
- Email: {ctx.email}
- Password: {ctx.password}

STEPS:
1. Navigate to https://console.flotorch.cloud/
2. Enter the email from TEST DATA into the email field.
3. Enter the password from TEST DATA into the password field.
4. Submit / click Login.
5. Wait until either the main console/dashboard loads OR an authentication error is visible.

EXPECTED RESULT (PASS):
- User lands on the authenticated console (dashboard or main app shell), not the sign-in form.

EXPECTED RESULT (FAIL):
- Any inline or toast error indicating invalid credentials, incorrect password, user not found, or similar.
- After a reasonable wait, the URL or UI still shows only the login form with no dashboard.

TERMINATION (MANDATORY):
- If and only if EXPECTED RESULT (PASS) is satisfied, finish using the "done" tool with success=true.
  Summarize what confirms you are logged in (e.g. visible navigation, workspace list, user menu).
- If EXPECTED RESULT (FAIL) is satisfied, finish using the "done" tool with success=false.
  Quote or paraphrase the exact error text you see. Do not keep retrying the same credentials indefinitely.
- Do not perform provider, workspace, model, dataset, or evaluation actions in this task.
"""


def _phase_scope_footer(*, scope: str, then_done: bool = True) -> str:
    done_line = (
        f'- When {scope} is fully complete (or explicitly SKIPped above), call "done" with success=true and stop.'
        if then_done
        else ""
    )
    return f"""
PHASE SCOPE (STRICT):
- Execute ONLY what this phase describes — {scope}.
- Do NOT start work from a later phase.
{done_line}
- If you are unexpectedly on the login page, use "done" with success=false.
"""


def _workflow_header(*, prerequisite: str) -> str:
    return f"""
PREREQUISITE: {prerequisite}
If you are unexpectedly on the login page, use "done" with success=false and explain — do not invent credentials.

SCOPE RULE — THIS PHASE ONLY:
- Execute ONLY the steps described below. Do NOT add, reorder, or invent steps.
- Do NOT create organization providers, workspace providers, models, datasets, evaluations, or anything outside this phase's scope.
- Do NOT generate your own plan — follow the exact sequence given.
- If you see steps or actions not described below, SKIP them and stay on task.

Wait for pages to fully load before interacting. After any Save/Create/Submit, wait for success confirmation before continuing.
If a form field doesn't match exactly, use the closest option available in the UI.

EXECUTION RULES (SPEED + STABILITY):
- Do NOT use write_file/replace_file or maintain todo.md.
- **Stay on https://console.flotorch.cloud/** unless the task explicitly says otherwise. Vendor model ids from .env (e.g. `amazon.nova-micro-v1:0`) are selected in **dropdowns**, not by navigating to `https://amazon.nova` or similar URLs.
- Prefer direct actions over bookkeeping; keep each step minimal.
- Avoid redundant re-check loops unless a required verification fails.
- Do NOT create or maintain a plan/todo; execute directly.
- For each modal/form, batch actions: fill all visible required fields first, then submit (avoid one-field-per-step behavior).
- OPTIONAL FIELDS: If a field is labeled optional, or the UI shows it is not required, do NOT fill it — leave default/empty and continue.

CRITICAL RULES FOR ALL FORMS AND MODALS:
1. This application uses modal dialogs (popups) for creating items.
2. The Save/Create/Submit button is ALWAYS at the bottom of the modal — it may be HIDDEN below the visible area.
3. After filling in ALL form fields, SCROLL DOWN INSIDE the modal/dialog to make the button visible.
4. To scroll inside a modal: use the scroll action on the **inner** scrollable form column (not only the outer dialog shell), or press Tab multiple times to reach the button.
5. NEVER skip a step because you cannot find the Create button — it exists, just scroll down to find it.
6. As a last resort, press Tab key repeatedly until the Create/Submit button gets focus, then press Enter.

COMBOBOX / "PROVIDER" SELECTS (VUETIFY-STYLE):
- A click on a dropdown option does NOT count as "selected" until you see real UI confirmation: in FloTorch, the chosen option row shows a **checkmark/tick** while the list is open, and after close the **trigger** shows the chosen label (not placeholder, not empty).
- Do not trust your own prior step summary for selection state — re-read the tick (when list open) and trigger text (when closed) before typing credentials.
- Never type secrets until that visible check passes.
- For **floating** provider lists: always **scroll inside the overlay/listbox** so the target row is fully on-screen before clicking; clipped options often log "clicked" but do not update `selected`. If selection fails twice, change strategy (scroll + wait, then keyboard navigate-until-label-matches + Enter) instead of repeating the same index click.

{provider_service_and_type_select_all()}

"""


# --- Phase 1: Login (build_task_login above) ---


def build_task_org_provider_phase(ctx: RunContext) -> str:
    """Phase 2 — organization (global) provider."""
    preconditions = f"""
PRECONDITIONS (mandatory — do not start if unmet):
- {_LOGIN_PASS}
- You must be on the authenticated FloTorch console (not the sign-in page).

If you land on the login page, call "done" with success=false immediately — do not create providers.
"""
    return "".join(
        [
            _workflow_header(prerequisite=_LOGIN_PASS),
            preconditions,
            step_org_provider(ctx),
            _phase_scope_footer(scope="Org / global provider creation (Step 2) or SKIP"),
        ]
    )


def build_task_workspace_phase(ctx: RunContext, *, org_phase_ran: bool = True) -> str:
    """Phase 3 — workspace create and enter."""
    if org_phase_ran:
        prerequisite = (
            f"{_LOGIN_PASS} Phase 2 Org provider completed (or explicitly SKIPped in Step 2)."
        )
        org_pre = "- Phase 2 Org provider: completed or SKIPped (full suite).\n"
    else:
        prerequisite = (
            f"{_LOGIN_PASS} (Phase 2 Org provider was **skipped** — prompt_partials / short suite.)"
        )
        org_pre = "- Phase 2 Org provider: not run in this suite mode.\n"
    preconditions = f"""
PRECONDITIONS (mandatory — do not start if unmet):
- {_LOGIN_PASS}
{org_pre}- Do not create or enter a workspace while still on the sign-in page.

If you are on the login page, call "done" with success=false — downstream workspace tests cannot run.
"""
    return "".join(
        [
            _workflow_header(prerequisite=prerequisite),
            preconditions,
            step_create_and_enter_workspace(ctx),
            _phase_scope_footer(scope="Workspace creation and entering the workspace (Steps 3–4)"),
        ]
    )


def build_task_workspace_provider_phase(ctx: RunContext) -> str:
    """Phase 4 — workspace-level LLM provider."""
    return "".join(
        [
            _workflow_header(prerequisite=_INSIDE_WORKSPACE),
            step_workspace_provider(ctx),
            _phase_scope_footer(scope="Workspace-level LLM provider (Step 5)"),
        ]
    )


def build_task_models_phase(ctx: RunContext) -> str:
    """Phase 5 — chat models + embedding model."""
    return "".join(
        [
            _workflow_header(prerequisite=_INSIDE_WORKSPACE),
            step_chat_models(ctx),
            step_embedding_model(ctx),
            _phase_scope_footer(scope="Chat models and embedding model (Steps 6–7)"),
        ]
    )


def build_task_chat_models_only_phase(ctx: RunContext) -> str:
    """Chat models only — used before prompt partials + Playground (no embedding)."""
    return "".join(
        [
            _workflow_header(prerequisite=_INSIDE_WORKSPACE),
            """
EXECUTION ORDER (strict):
1. Model Registry → Models → create **one** FloTorch chat model per Step 6 below (org provider, base model, Save, Publish).
2. Do **not** create a second chat model, prompt partials, or Playground in this phase — the next phase handles those.
""",
            step_chat_model_for_prompt_partials(ctx),
            _phase_scope_footer(scope="One chat model (Step 6) — required before Prompt Partials"),
        ]
    )


def build_task_vector_providers_phase(ctx: RunContext) -> str:
    """Phase 6 — vector storage providers."""
    return "".join(
        [
            _workflow_header(prerequisite=_INSIDE_WORKSPACE),
            step_vector_storage_providers(ctx),
            _phase_scope_footer(scope="Vector storage provider creation (Step 8)"),
        ]
    )


def build_task_vector_repositories_phase(ctx: RunContext) -> str:
    """Phase 7 — vector storage repositories."""
    return "".join(
        [
            _workflow_header(prerequisite=_INSIDE_WORKSPACE),
            step_vector_repositories(ctx),
            _phase_scope_footer(scope="Vector storage repository creation (Step 9)"),
        ]
    )


def build_task_datasets_phase(ctx: RunContext) -> str:
    """Phase 8 — LLM dataset then RAG datasets."""
    return "".join(
        [
            _workflow_header(prerequisite=_INSIDE_WORKSPACE),
            step_dataset(ctx),
            step_rag_datasets(ctx),
            _phase_scope_footer(scope="LLM dataset then RAG datasets (Steps 11 and 10)"),
        ]
    )


def build_task_eval_datasets_phase(ctx: RunContext) -> str:
    """Datasets required by FLOTORCH_EVAL_TYPES (evaluations workflow only)."""
    types = _active_eval_types(ctx)
    steps: list[str] = []
    scope_parts: list[str] = []
    if "llm" in types or "prompt" in types:
        steps.append(step_dataset(ctx))
        scope_parts.append("LLM dataset")
    if "rag" in types:
        steps.append(step_rag_datasets(ctx))
        scope_parts.append("RAG dataset")
    if "agent" in types or "workflow" in types:
        steps.append(step_agent_dataset(ctx))
        scope_parts.append("agent workflow evaluation dataset")
    return "".join(
        [
            _workflow_header(prerequisite=_INSIDE_WORKSPACE),
            *steps,
            _phase_scope_footer(scope=" and ".join(scope_parts)),
        ]
    )


def build_task_guardrails_phase(ctx: RunContext) -> str:
    """Guardrails suite: create guardrails → one model with Input Guardrails → Playground."""
    test_model = guardrail_test_model_name(ctx.uid)
    guardrail_step = step_guardrails_sanity_create(ctx)
    guardrail_label = "sanity guardrails (exactly 4: Custom/Replace, AWS/Block, SS/Redact, Phone/Log)"
    return "".join(
        [
            _workflow_header(prerequisite=_INSIDE_WORKSPACE),
            f"""
GUARDRAILS-ONLY PHASE — STRICT SCOPE:
- The org provider ({ctx.first_provider['name'] if ctx.first_provider else 'N/A'}) and workspace already exist from earlier phases.
- Do NOT create any organization providers, workspace providers, LLM models, embedding models, or datasets.
- Do NOT navigate to Provider sections, Dataset sections, or Evaluation sections.
- Do NOT create any FloTorch chat models beyond the single guardrail-test model described below.

EXECUTION ORDER (strict — complete each block before the next):
1. **Create {guardrail_label}**
2. **One model only** — Model Registry → Models → single Published pipeline `{test_model}`:
   - Attach sanity guardrails per model step, then org provider + **base model from FloTorch/.env** + Publish.
   - Do **not** create standard Step 6 chat models (no two-model flow, no `-2` suffix, no embedding).
3. **Playground** — FloTorch Models = `{test_model}` only; run keyword guardrail queries.
""",
            guardrail_step,
            step_guardrail_test_model(ctx),
            step_playground_validate_guardrails(ctx),
            playground_guardrails_final_summary(ctx),
            _phase_scope_footer(
                scope=(
                    "sanity guardrails, then one model with revision updates, "
                    "then Playground sanity validation"
                )
            ),
        ]
    )


def _active_eval_types(ctx: RunContext) -> list[str]:
    """Eval types for .env / legacy paths. Empty ctx.eval_types → default llm+prompt+rag."""
    if ctx.eval_types:
        return ctx.eval_types
    return ["llm", "prompt", "rag"]


def _evaluation_types(ctx: RunContext) -> list[str]:
    """Eval types for execution.py evaluations test case. Empty → skip evaluations."""
    return list(ctx.eval_types) if ctx.eval_types else []


# Preconditions per evaluation type (setup only — not test cases).
_EVAL_PREREQ_DOCS: dict[str, str] = {
    "llm": "workspace_provider, models (2 chat + embedding), datasets (llm-evals)",
    "prompt": "same as llm",
    "rag": "llm path + vector_providers, vector_repos, RAG dataset",
    "agent": "models (1 org chat), datasets (agent-dataset)",
    "workflow": "models (1 org chat), datasets (agent-dataset)",
}

_TEST_CASE_MODULES = ("guardrails", "prompt_partials", "evaluations")


def eval_prerequisites(types: list[str]) -> dict[str, bool]:
    """Map EVAL_TYPES → prerequisite setup flags (not test cases)."""
    t = set(types)
    needs_llm_prompt_rag = bool(t & {"llm", "prompt", "rag"})
    needs_agent_workflow = bool(t & {"agent", "workflow"})
    return {
        "workspace_provider": needs_llm_prompt_rag,
        "models_full": needs_llm_prompt_rag,
        "models_org_single": needs_agent_workflow and not needs_llm_prompt_rag,
        "vector_providers": "rag" in t,
        "vector_repos": "rag" in t,
        "datasets": _eval_needs_datasets(types),
    }


def _test_cases_for_modules_all(ctx: RunContext) -> list[str]:
    """MODULES='all' test cases: guardrails + prompt_partials + evaluations (if EVAL_TYPES set)."""
    cases = ["guardrails", "prompt_partials"]
    if _evaluation_types(ctx):
        cases.append("evaluations")
    return cases


def precondition_requirements(ctx: RunContext, test_cases: list[str]) -> dict[str, bool]:
    """Setup phases required before the selected test cases run."""
    eval_types = _evaluation_types(ctx)
    req = eval_prerequisites(eval_types)
    needs_models = False
    models_full = req["models_full"]
    models_org_single = req["models_org_single"]
    if "prompt_partials" in test_cases and not models_full:
        models_org_single = True
        needs_models = True
    if models_full or models_org_single:
        needs_models = True
    return {
        "org_provider": True,
        "workspace": True,
        "workspace_provider": req["workspace_provider"],
        "models_full": models_full,
        "models_org_single": models_org_single and not models_full,
        "needs_models": needs_models,
        "vector_providers": req["vector_providers"],
        "vector_repos": req["vector_repos"],
        "datasets": req["datasets"] and "evaluations" in test_cases,
    }


def print_execution_plan_summary(ctx: RunContext) -> None:
    """Log test cases and prerequisites for execution.py."""
    test_cases = _test_cases_for_modules_all(ctx)
    print(f"  Test cases (MODULES=all): {', '.join(test_cases)}")
    eval_types = _evaluation_types(ctx)
    if eval_types:
        print("  Evaluation prerequisites:")
        for name in eval_types:
            doc = _EVAL_PREREQ_DOCS.get(name, "see tasks.py")
            print(f"    - {name}: {doc}")
    pre = precondition_requirements(ctx, test_cases)
    pre_labels = ["org_provider", "workspace"]
    if pre["workspace_provider"]:
        pre_labels.append("workspace_provider")
    if pre["needs_models"]:
        pre_labels.append("models (full)" if pre["models_full"] else "models (1 org chat)")
    if pre["vector_providers"]:
        pre_labels.extend(["vector_providers", "vector_repos"])
    if pre["datasets"]:
        pre_labels.append("datasets")
    print(f"  Preconditions (auto): {', '.join(pre_labels)}")


def normalize_execution_modules(modules, ctx: RunContext) -> list[str]:
    """Resolve MODULES from execution.py (all, list, or comma-separated str)."""
    if isinstance(modules, str) and modules.strip().lower() == "all":
        return _derive_modules_all(ctx)
    # execution.py: empty EVAL_TYPES means skip evaluations — do not fall back to .env defaults.
    eval_types = _evaluation_types(ctx)
    if isinstance(modules, str):
        base = [m.strip().lower() for m in modules.split(",") if m.strip()]
    elif isinstance(modules, list):
        base = [str(m).strip().lower() for m in modules if str(m).strip()]
    else:
        return _derive_modules_all(ctx)
    return _ensure_eval_prerequisites(base, eval_types)


def _derive_modules_all(ctx: RunContext) -> list[str]:
    """MODULES='all' → preconditions + test cases + close."""
    test_cases = _test_cases_for_modules_all(ctx)
    pre = precondition_requirements(ctx, test_cases)
    mods: list[str] = ["org_provider", "workspace"]
    if pre["workspace_provider"]:
        mods.append("workspace_provider")
    if pre["needs_models"]:
        mods.append("models")
    if pre["vector_providers"]:
        mods.append("vector_providers")
    if pre["vector_repos"]:
        mods.append("vector_repos")
    if pre["datasets"]:
        mods.append("datasets")
    mods.extend(test_cases)
    mods.append("close")
    return mods


def _ensure_eval_prerequisites(modules: list[str], types: list[str]) -> list[str]:
    """Auto-inject missing prerequisite modules for explicit MODULES lists."""
    req = eval_prerequisites(types)
    mods = list(modules)
    mod_set = set(mods)
    added: list[str] = []

    if "org_provider" not in mod_set:
        added.append("org_provider")
        mods.insert(0, "org_provider")
        mod_set.add("org_provider")
    if req["workspace_provider"] and "workspace_provider" not in mod_set:
        added.append("workspace_provider")
        if "models" in mod_set:
            mods.insert(mods.index("models"), "workspace_provider")
        else:
            mods.append("workspace_provider")
        mod_set.add("workspace_provider")
    if (req["models_full"] or req["models_org_single"]) and "models" not in mod_set:
        added.append("models")
        mods.append("models")
        mod_set.add("models")
    if req["datasets"] and "datasets" not in mod_set and "evaluations" in mod_set:
        added.append("datasets")
        idx = mods.index("evaluations") if "evaluations" in mod_set else len(mods)
        mods.insert(idx, "datasets")
        mod_set.add("datasets")
    if added:
        print(f"  Auto-added prerequisite modules: {', '.join(added)}")
    return mods


def workspace_phases_from_execution_plan(modules, ctx: RunContext) -> list[tuple[str, str, int, bool]]:
    """Build workspace phases (4+) from execution.py MODULES + EVAL_TYPES."""
    eval_types = _evaluation_types(ctx)
    mod_list = normalize_execution_modules(modules, ctx)
    mod_set = set(mod_list)
    test_cases = [m for m in mod_list if m in _TEST_CASE_MODULES]
    pre = precondition_requirements(ctx, test_cases or _test_cases_for_modules_all(ctx))
    phases: list[tuple[str, str, int, bool]] = []

    if pre["workspace_provider"] and "workspace_provider" in mod_set:
        phases.append(("Workspace LLM provider", "build_task_workspace_provider_phase", 55, False))
    if "models" in mod_set:
        if pre["models_full"]:
            phases.append(("Models (chat + embedding)", "build_task_models_phase", 130, False))
        elif pre["models_org_single"]:
            phases.append(("Model (org-level, single)", "build_task_chat_models_only_phase", 90, False))
    if pre["vector_providers"] and "vector_providers" in mod_set:
        phases.append(("Vector storage providers", "build_task_vector_providers_phase", 90, False))
    if pre["vector_repos"] and "vector_repos" in mod_set:
        phases.append(("Vector repositories", "build_task_vector_repositories_phase", 80, False))
    if pre["datasets"] and "datasets" in mod_set:
        phases.append(
            (
                "Datasets (eval-specific)",
                "build_task_eval_datasets_phase",
                100,
                _eval_datasets_need_files(eval_types),
            )
        )
    if "guardrails" in mod_set:
        phases.append(
            (
                "Guardrails + test model + Playground",
                "build_task_guardrails_phase",
                480,
                False,
            )
        )
    if "prompt_partials" in mod_set:
        phases.append(
            ("Prompt Partials + Playground", "build_task_prompt_partials_standalone_phase", 100, False)
        )
    if "evaluations" in mod_set and eval_types:
        eval_max_steps = 150 if "workflow" in eval_types else 120
        phases.append(
            (
                f"Evaluations ({_eval_type_label(eval_types)})",
                "build_task_evaluations_standalone_phase",
                eval_max_steps,
                "prompt" in eval_types,
            )
        )
    if "close" in mod_set:
        has_eval = bool(eval_types) and "evaluations" in mod_set
        close_builder = (
            "build_task_suite_close_evaluations_phase" if has_eval else "build_task_suite_close_phase"
        )
        phases.append(("Close test suite", close_builder, 25, False))
    return phases


def _eval_type_label(types: list[str]) -> str:
    if set(types) == {"llm", "prompt", "rag"}:
        return "LLM, Prompt, RAG"
    return ", ".join(t.upper() for t in types)


def _build_eval_steps(ctx: RunContext) -> str:
    types = _active_eval_types(ctx)
    parts: list[str] = []
    if "llm" in types:
        parts.append(step_llm_evaluation(ctx))
    if "prompt" in types:
        parts.append(step_prompt_evaluation(ctx))
    if "rag" in types:
        parts.append(step_rag_evaluations(ctx))
    if "agent" in types:
        parts.append(step_agent_evaluation(ctx))
    if "workflow" in types:
        parts.append(step_workflow_evaluation(ctx))
    return "".join(parts)


def _eval_execution_order(types: list[str]) -> str:
    lines = []
    idx = 1
    if "llm" in types:
        lines.append(f"{idx}. **LLM Model Evaluation** — dataset `llm-evals-{{uid}}`")
        idx += 1
    if "prompt" in types:
        lines.append(f"{idx}. **Prompt Evaluation** — reuse same dataset; upload prompt JSON from Dataset/")
        idx += 1
    if "rag" in types:
        lines.append(f"{idx}. **RAG Evaluation** — only if vector path exists in .env; otherwise SKIP per step text")
        idx += 1
    if "agent" in types:
        lines.append(f"{idx}. **Agent Evaluation** — create/publish agent; attach org chat model pipeline")
        idx += 1
    if "workflow" in types:
        lines.append(f"{idx}. **Workflow Evaluation** — agents + workflow canvas + publish + run")
        idx += 1
    return "\n".join(lines)


def _eval_needs_vector(types: list[str]) -> bool:
    """Vector storage/repos are only required for RAG evaluation."""
    return "rag" in types


def _eval_needs_datasets(types: list[str]) -> bool:
    return bool(set(types) & {"llm", "prompt", "rag", "agent", "workflow"})


def _eval_datasets_need_files(types: list[str]) -> bool:
    return _eval_needs_datasets(types)


def build_task_evaluations_phase(ctx: RunContext) -> str:
    """Phase 9 — eval steps filtered by FLOTORCH_EVAL_TYPES."""
    types = _active_eval_types(ctx)
    return "".join(
        [
            _workflow_header(
                prerequisite=_INSIDE_WORKSPACE
                + " LLM and RAG datasets from the prior Datasets phase are created."
            ),
            _build_eval_steps(ctx),
            _phase_scope_footer(
                scope=f"Evaluations screen: {_eval_type_label(types)}"
            ),
        ]
    )


def build_task_workflow_evaluation_standalone_phase(ctx: RunContext) -> str:
    """Login + workspace only — run workflow canvas + evaluation (prerequisites must exist)."""
    return "".join(
        [
            _workflow_header(prerequisite=_INSIDE_WORKSPACE),
            """
**FLOTORCH_WORKFLOW=workflow_evaluation:** prerequisites (chat model, agent dataset, agents) must already exist.
Do **not** create models, datasets, or org/workspace providers in this phase.

EXECUTION ORDER (strict — complete each before the next):
1. **Workflow** — Agents → Workflow: create, layout, connect edges, publish.
2. **Workflow Evaluation** — Evaluations → run workflow evaluation job.
""",
            step_workflow_evaluation(ctx),
            _phase_scope_footer(scope="Workflow Evaluation (workflow canvas + evaluation run)"),
        ]
    )


def build_task_evaluations_standalone_phase(ctx: RunContext) -> str:
    """Evaluations-only suite — steps filtered by FLOTORCH_EVAL_TYPES."""
    types = _active_eval_types(ctx)
    return "".join(
        [
            _workflow_header(
                prerequisite=_INSIDE_WORKSPACE
                + " Required datasets from the prior phase are created (if that phase ran)."
            ),
            f"""
**FLOTORCH_WORKFLOW=evaluations:** run evaluations only in this phase (datasets were created in the prior phase).

EXECUTION ORDER (strict — complete each before the next):
{_eval_execution_order(types)}
""".format(uid=ctx.uid),
            _build_eval_steps(ctx),
            _phase_scope_footer(
                scope=f"Evaluations: {_eval_type_label(types)}"
            ),
        ]
    )


def _build_task_prompt_partials_phase_impl(
    ctx: RunContext,
    *,
    prerequisite: str,
    single_chat_model: bool = False,
) -> str:
    return "".join(
        [
            _workflow_header(prerequisite=prerequisite),
            """
EXECUTION ORDER (strict — complete each block before the next):
1. **Models** — must already exist from the prior phase (Published FloTorch chat model(s); Step 6).
2. **Prompt partials** — Prompts → Partials: create partial, two versions, publish both, Publish Latest.
3. **Playground validation** — Playground → Models: select custom model from step 1; run partial probe queries.
""",
            step_prompt_partials(ctx),
            step_playground_validate_prompt_partial(
                ctx,
                step6_models_created=True,
                single_chat_model=single_chat_model,
            ),
            partials_final_summary(ctx),
            playground_final_summary(
                ctx,
                step6_models_created=True,
                single_chat_model=single_chat_model,
            ),
            _phase_scope_footer(scope="Prompt Partials then Playground validation"),
        ]
    )


def build_task_prompt_partials_phase(ctx: RunContext) -> str:
    """Full suite — partials after evaluations."""
    return _build_task_prompt_partials_phase_impl(
        ctx,
        prerequisite=_INSIDE_WORKSPACE + " Evaluations phase completed.",
    )


def build_task_prompt_partials_standalone_phase(ctx: RunContext) -> str:
    """Partials-only suite — one chat model was created in the immediately prior phase."""
    return _build_task_prompt_partials_phase_impl(
        ctx,
        prerequisite=(
            _INSIDE_WORKSPACE
            + " One chat model created and Published in the prior Models phase (required for Playground)."
        ),
        single_chat_model=True,
    )


def build_task_suite_close_phase(ctx: RunContext) -> str:
    """Phase 11 — close the test suite."""
    return "".join(
        [
            _workflow_header(prerequisite="All functional phases through Prompt Partials are complete."),
            step_suite_close(ctx),
            _phase_scope_footer(scope="Suite close and FINAL SUMMARY only"),
        ]
    )


def build_task_suite_close_evaluations_phase(ctx: RunContext) -> str:
    """Close evaluations-focused suite."""
    return "".join(
        [
            _workflow_header(prerequisite="Evaluations phase completed (LLM, Prompt, and RAG if applicable)."),
            step_suite_close_evaluations(ctx),
            _phase_scope_footer(scope="Suite close and evaluations FINAL SUMMARY only"),
        ]
    )


def build_task_workflow(ctx: RunContext) -> str:
    """Legacy single combined prompt (all phases concatenated)."""
    return "".join(
        [
            build_task_org_provider_phase(ctx),
            build_task_workspace_phase(ctx, org_phase_ran=True),
            build_task_workspace_provider_phase(ctx),
            build_task_models_phase(ctx),
            build_task_vector_providers_phase(ctx),
            build_task_vector_repositories_phase(ctx),
            build_task_datasets_phase(ctx),
            build_task_evaluations_phase(ctx),
            build_task_guardrails_phase(ctx),
            build_task_prompt_partials_phase(ctx),
            build_task_suite_close_phase(ctx),
        ]
    )


# Backward-compatible aliases
build_task_workspace_level = build_task_workflow


def build_task_prompt_partials_workspace_level(ctx: RunContext) -> str:
    """Partials-only workspace phase (prompt_partials workflow mode)."""
    return "".join(
        [
            build_task_prompt_partials_phase(ctx),
            build_task_suite_close_phase(ctx),
        ]
    )


def build_task_prompt_partials_workflow(ctx: RunContext) -> str:
    return "".join(
        [
            build_task_workspace_phase(ctx, org_phase_ran=False),
            build_task_prompt_partials_workspace_level(ctx),
        ]
    )


LOGIN_GATE_FAILED_REASON = "TC-01 login gate failed — suite aborted"


def _evaluations_suite_workspace_phase_specs(
    ctx: RunContext | None = None,
) -> list[tuple[str, str, int, bool]]:
    """Phases for FLOTORCH_WORKFLOW=evaluations — filtered by FLOTORCH_EVAL_TYPES."""
    types = _active_eval_types(ctx) if ctx is not None else ["llm", "prompt", "rag"]
    req = eval_prerequisites(types)
    phases: list[tuple[str, str, int, bool]] = []

    if req["workspace_provider"]:
        phases.append(("Workspace LLM provider", "build_task_workspace_provider_phase", 55, False))
    if req["models_full"]:
        phases.append(("Models (chat + embedding)", "build_task_models_phase", 130, False))
    elif req["models_org_single"]:
        phases.append(("Model (org-level, single)", "build_task_chat_models_only_phase", 90, False))

    if _eval_needs_vector(types):
        phases.extend(
            [
                ("Vector storage providers", "build_task_vector_providers_phase", 90, False),
                ("Vector repositories", "build_task_vector_repositories_phase", 80, False),
            ]
        )
    if _eval_needs_datasets(types):
        phases.append(
            ("Datasets (eval-specific)", "build_task_eval_datasets_phase", 100, _eval_datasets_need_files(types))
        )
    eval_max_steps = 150 if "workflow" in types else 120
    phases.extend(
        [
            (
                f"Evaluations ({_eval_type_label(types)})",
                "build_task_evaluations_standalone_phase",
                eval_max_steps,
                "prompt" in types,
            ),
            ("Close test suite", "build_task_suite_close_evaluations_phase", 25, False),
        ]
    )
    return phases


def _full_suite_workspace_phase_specs() -> list[tuple[str, str, int, bool]]:
    """Ordered phases inside workspace after Phase 3 (label, builder name, max_steps, needs_files)."""
    phases: list[tuple[str, str, int, bool]] = [
        ("Phase 4: Workspace LLM provider", "build_task_workspace_provider_phase", 55, False),
        ("Phase 5: Model creation", "build_task_models_phase", 130, False),
        ("Phase 6: Vector storage providers", "build_task_vector_providers_phase", 90, False),
        ("Phase 7: Vector repositories", "build_task_vector_repositories_phase", 80, False),
        ("Phase 8: Datasets (LLM + RAG)", "build_task_datasets_phase", 100, True),
        ("Phase 9: Evaluations (LLM, Prompt, RAG)", "build_task_evaluations_phase", 120, True),
        (
            "Phase 10: Guardrails + test model + Playground",
            "build_task_guardrails_phase",
            480,
            False,
        ),
        ("Phase 11: Prompt Partials", "build_task_prompt_partials_phase", 100, False),
        ("Phase 12: Close test suite", "build_task_suite_close_phase", 25, False),
    ]
    return phases


def workflow_runs_org_provider(workflow_mode: str) -> bool:
    """Org provider (Phase 2) is required before workspace for focused suites."""
    mode = (workflow_mode or "full").strip().lower()
    if mode == "workflow_evaluation":
        return False
    return mode in ("full", "guardrails", "prompt_partials", "partials", "evaluations")


def workspace_phases_for_workflow_mode(
    workflow_mode: str,
    *,
    ctx: RunContext | None = None,
) -> list[tuple[str, str, int, bool]]:
    """Phases 4+ after workspace entry: (label, builder_name, max_steps, needs_files)."""
    mode = (workflow_mode or "full").strip().lower()
    if mode == "full":
        return _full_suite_workspace_phase_specs()
    if mode == "guardrails":
        return [
            (
                "Guardrails: regression create → one model (guardrail-test) → Playground",
                "build_task_guardrails_phase",
                480,
                False,
            ),
            ("Close test suite", "build_task_suite_close_phase", 25, False),
        ]
    if mode in ("prompt_partials", "partials"):
        return [
            ("One chat model (for Playground)", "build_task_chat_models_only_phase", 90, False),
            (
                "Prompt Partials + Playground",
                "build_task_prompt_partials_standalone_phase",
                100,
                False,
            ),
            ("Close test suite", "build_task_suite_close_phase", 25, False),
        ]
    if mode == "evaluations":
        return _evaluations_suite_workspace_phase_specs(ctx)
    if mode == "workflow_evaluation":
        return [
            (
                "Workflow Evaluation",
                "build_task_workflow_evaluation_standalone_phase",
                200,
                False,
            ),
        ]
    return []


def execution_plan_label(ctx: RunContext, modules) -> str:
    """Human-readable execution plan line for reports."""
    eval_types = _evaluation_types(ctx)
    eval_part = ", ".join(eval_types) if eval_types else "none (guardrails + prompt_partials only)"
    mod_repr = modules if isinstance(modules, str) else ", ".join(modules)
    return f"execution.py · MODULES={mod_repr} · EVAL_TYPES={eval_part}"


def suite_phase_titles_for_execution(ctx: RunContext, modules) -> list[str]:
    """Phase labels for execution.py plan (login gate FAIL list)."""
    mod_list = normalize_execution_modules(modules, ctx)
    titles: list[str] = []
    if "org_provider" in mod_list:
        titles.append("Phase 2: Org provider")
    titles.append("Phase 3: Workspace create and enter")
    titles.extend(label for label, _, _, _ in workspace_phases_from_execution_plan(modules, ctx))
    return titles


def _single_shot_login(ctx: RunContext) -> str:
    return f"""
==============================
STEP 1: LOGIN
==============================
- Go to https://console.flotorch.cloud/
- Enter email: {ctx.email}
- Enter password: {ctx.password}
- Click Login
- Wait for dashboard to fully load (not on /auth/signin)
"""


def _single_shot_eval_steps(ctx: RunContext) -> str:
    types = _evaluation_types(ctx)
    if not types:
        return """
==============================
EVALUATIONS: SKIP — EVAL_TYPES empty in FloTorch/execution.py
==============================
"""
    parts: list[str] = []
    if "llm" in types:
        parts.append(step_llm_evaluation(ctx))
    if "prompt" in types:
        parts.append(step_prompt_evaluation(ctx))
    if "rag" in types:
        parts.append(step_rag_evaluations(ctx))
    if "agent" in types:
        parts.append(step_agent_evaluation(ctx))
    if "workflow" in types:
        parts.append(step_workflow_evaluation(ctx))
    return "".join(parts)


def _single_shot_final_summary(ctx: RunContext, mod_list: list[str]) -> str:
    lines = [
        "1. Login status",
        "2. Org provider created or skipped",
        f"3. Workspace `{ctx.workspace_name}` created and entered",
    ]
    if "guardrails" in mod_list:
        lines.append(f"4. Guardrails + model `{guardrail_test_model_name(ctx.uid)}` + Playground validation")
    if "prompt_partials" in mod_list:
        lines.append("5. Prompt partials + Playground validation")
    if "evaluations" in mod_list and _evaluation_types(ctx):
        lines.append(f"6. Evaluations ({_eval_type_label(_evaluation_types(ctx))})")
    return f"""
==============================
FINAL SUMMARY
==============================
After all steps, report back:
{chr(10).join(lines)}
"""


def build_task_single_shot_from_execution_plan(ctx: RunContext, modules) -> str:
    """One Agent.run() prompt driven by FloTorch/execution.py MODULES + EVAL_TYPES."""
    mod_list = normalize_execution_modules(modules, ctx)
    mod_set = set(mod_list)
    test_cases = [m for m in mod_list if m in _TEST_CASE_MODULES]
    pre = precondition_requirements(ctx, test_cases or _test_cases_for_modules_all(ctx))
    eval_types = _evaluation_types(ctx)

    parts: list[str] = [
        """
You are automating a FloTorch QA workflow on https://console.flotorch.cloud/. Follow every step in order.
Always wait for pages to fully load. After Save/Create/Submit, wait for confirmation before proceeding.
Do NOT call "done" or stop until the FINAL SUMMARY at the end.

""",
        provider_service_and_type_select_all(),
        _single_shot_login(ctx),
    ]

    if "org_provider" in mod_set:
        parts.append(step_org_provider(ctx))

    parts.append(step_create_and_enter_workspace(ctx))

    if pre["workspace_provider"] and "workspace_provider" in mod_set:
        parts.append(step_workspace_provider(ctx))
    if "models" in mod_set:
        if pre["models_full"]:
            parts.append(step_chat_models(ctx))
            parts.append(step_embedding_model(ctx))
        elif pre["models_org_single"]:
            parts.append(step_chat_model_for_prompt_partials(ctx))
    if pre["vector_providers"] and "vector_providers" in mod_set:
        parts.append(step_vector_storage_providers(ctx))
    if pre["vector_repos"] and "vector_repos" in mod_set:
        parts.append(step_vector_repositories(ctx))
    if pre["datasets"] and "datasets" in mod_set:
        if "llm" in eval_types or "prompt" in eval_types:
            parts.append(step_dataset(ctx))
        if "rag" in eval_types:
            parts.append(step_rag_datasets(ctx))
        if "agent" in eval_types or "workflow" in eval_types:
            parts.append(step_agent_dataset(ctx))
    if "guardrails" in mod_set:
        test_model = guardrail_test_model_name(ctx.uid)
        parts.append(f"""
==============================
GUARDRAILS TEST CASE
==============================
Create 4 sanity guardrails (Custom/Replace, AWS/Block, SS/Redact, Phone/Log),
then one published model `{test_model}` with Input Guardrails attached,
then validate guardrail behavior in Playground.
Do NOT create extra chat models, embedding models, or datasets in this block.
""")
        parts.append(step_guardrails_sanity_create(ctx))
        parts.append(step_guardrail_test_model(ctx))
        parts.append(step_playground_validate_guardrails(ctx))
        parts.append(playground_guardrails_final_summary(ctx))
    if "prompt_partials" in mod_set:
        parts.append(step_prompt_partials(ctx))
        parts.append(step_playground_validate_prompt_partial(ctx))
        parts.append(partials_final_summary(ctx))
    if "evaluations" in mod_set and eval_types:
        parts.append(_single_shot_eval_steps(ctx))

    parts.append(_single_shot_final_summary(ctx, mod_list))
    return "".join(parts)


def suite_phase_titles_for_report(
    *,
    workflow_mode: str = "full",
    ctx: RunContext | None = None,
    execution_modules=None,
) -> list[str]:
    """Phase labels used when login fails so every downstream case is reported FAIL."""
    if execution_modules is not None and ctx is not None:
        return suite_phase_titles_for_execution(ctx, execution_modules)
    mode = (workflow_mode or "full").strip().lower()
    if mode == "guardrails":
        return [
            "Phase 2: Org provider",
            "Phase 3: Workspace create and enter",
            "Guardrails: regression create → model w/ Input Guardrails → Playground",
            "Close test suite",
        ]
    if mode in ("prompt_partials", "partials"):
        return [
            "Phase 2: Org provider",
            "Phase 3: Workspace create and enter",
            "One chat model (for Playground)",
            "Prompt Partials + Playground",
            "Close test suite",
        ]
    if mode == "evaluations":
        titles = [
            "Phase 2: Org provider",
            "Phase 3: Workspace create and enter",
        ]
        titles.extend(label for label, _, _, _ in _evaluations_suite_workspace_phase_specs(ctx))
        return titles
    if mode == "workflow_evaluation":
        return [
            "Phase 3: Workspace create and enter",
            "Workflow Evaluation",
        ]
    titles = [
        "Phase 2: Org provider",
        "Phase 3: Workspace create and enter",
    ]
    titles.extend(label for label, _, _, _ in _full_suite_workspace_phase_specs())
    return titles


def full_suite_workspace_phases(ctx: RunContext) -> list[tuple[str, str, int, bool]]:
    """Ordered phases inside workspace after Phase 3 (label, builder name, max_steps, needs_files)."""
    return _full_suite_workspace_phase_specs()
