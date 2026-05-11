"""Agent task prompts: login and full post-login workflow."""

from FloTorch.config.run_context import RunContext
from FloTorch.prompts.steps.dataset import step_dataset
from FloTorch.prompts.steps.evaluation import final_summary, step_llm_evaluation, step_prompt_evaluation
from FloTorch.prompts.steps.models import step_chat_models, step_embedding_model
from FloTorch.prompts.steps.org_provider import step_org_provider
from FloTorch.prompts.steps.workspace import step_create_and_enter_workspace
from FloTorch.prompts.steps.workspace_provider import step_workspace_provider


def build_task_login(ctx: RunContext) -> str:
    return f"""
You execute exactly ONE test case. Do not start any other QA steps after login.

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


def _workflow_header() -> str:
    return """
You are automating a QA workflow on FloTorch. Follow each step in order.
PREREQUISITE: TC-01 (login) already passed in this browser session. You should already be authenticated.
If you are unexpectedly on the login page, use "done" with success=false and explain — do not invent credentials.

Wait for pages to fully load before interacting. After any Save/Create/Submit, wait for success confirmation before continuing.
If a form field doesn't match exactly, use the closest option available in the UI.

EXECUTION RULES (SPEED + STABILITY):
- Do NOT use write_file/replace_file or maintain todo.md.
- Prefer direct actions over bookkeeping; keep each step minimal.
- Avoid redundant re-check loops unless a required verification fails.
- Do NOT create or maintain a plan/todo; execute directly.
- For each modal/form, batch actions: fill all visible required fields first, then submit (avoid one-field-per-step behavior).
- OPTIONAL FIELDS: If a field is labeled optional, or the UI shows it is not required, do NOT fill it — leave default/empty and continue.

CRITICAL RULES FOR ALL FORMS AND MODALS:
1. This application uses modal dialogs (popups) for creating items.
2. The Save/Create/Submit button is ALWAYS at the bottom of the modal — it may be HIDDEN below the visible area.
3. After filling in ALL form fields, SCROLL DOWN INSIDE the modal/dialog to make the button visible.
4. To scroll inside a modal: use the scroll action on the modal element, or press Tab multiple times to reach the button.
5. NEVER skip a step because you cannot find the Create button — it exists, just scroll down to find it.
6. As a last resort, press Tab key repeatedly until the Create/Submit button gets focus, then press Enter.


"""


def build_task_workflow(ctx: RunContext) -> str:
    parts = [
        _workflow_header(),
        step_org_provider(ctx),
        step_create_and_enter_workspace(ctx),
        step_workspace_provider(ctx),
        step_chat_models(ctx),
        step_embedding_model(ctx),
        step_dataset(ctx),
        step_llm_evaluation(ctx),
        step_prompt_evaluation(ctx),
        final_summary(ctx),
    ]
    return "".join(parts)
