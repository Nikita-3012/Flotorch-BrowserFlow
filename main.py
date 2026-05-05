

from browser_use import Agent, ChatGoogle
from browser_use.browser import BrowserSession
from dotenv import load_dotenv
import os
import asyncio
from datetime import datetime, timezone

load_dotenv()

# ==============================
# FLOTORCH CREDENTIALS
# ==============================
email = os.getenv("FLOTORCH_EMAIL")
password = os.getenv("FLOTORCH_PASSWORD")

# ==============================
# RUN SUFFIX (UTC timestamp, microsecond precision)
# ==============================
uid = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
workspace_name = f"automation-{uid}"

# Agent must place this exact token in `memory` when Step 3 falls back to Default Workspace (detected in Python logs).
WORKSPACE_FALLBACK_TOKEN = "WORKSPACE_FALLBACK_DEFAULT"


# ==============================
# PROVIDER DETECTION
# ==============================
def env(key):
    val = os.getenv(key, "")
    return val.strip() if val else ""


PROVIDERS = []


def register(name, fields, supports_embedding=False):
    if all(v for v in fields.values()):
        PROVIDERS.append({
            "name": name,
            "fields": fields,
            "supports_embedding": supports_embedding,
        })


register("Groq", {
    "API Key": env("GROQ_API_KEY"),
}, supports_embedding=False)

register("Google Generative AI", {
    "API Key": env("GOOGLE_API_KEY"),
}, supports_embedding=True)

register("Google Vertex AI", {
    "Project ID": env("GOOGLE_VERTEX_PROJECT_ID"),
    "Region": env("GOOGLE_VERTEX_REGION"),
    "Service Account": env("GOOGLE_VERTEX_SERVICE_ACCOUNT"),
    "Private Key": env("GOOGLE_VERTEX_PRIVATE_KEY"),
}, supports_embedding=True)

register("OpenAI", {
    "API Key": env("OPENAI_API_KEY"),
}, supports_embedding=True)

register("Amazon Bedrock", {
    "Access Key": env("AMAZON_BEDROCK_ACCESS_KEY"),
    "Secret Key": env("AMAZON_BEDROCK_SECRET_KEY"),
    "Region": env("AMAZON_BEDROCK_REGION"),
}, supports_embedding=True)

register("Anthropic", {
    "API Key": env("ANTHROPIC_API_KEY"),
}, supports_embedding=False)

register("DeepSeek", {
    "API Key": env("DEEPSEEK_API_KEY"),
}, supports_embedding=False)

register("Azure OpenAI", {
    "API Key": env("AZURE_OPENAI_API_KEY"),
    "Base URL": env("AZURE_OPENAI_BASE_URL"),
    "API Version": env("AZURE_OPENAI_API_VERSION"),
}, supports_embedding=True)

register("Cohere", {
    "API Key": env("COHERE_API_KEY"),
}, supports_embedding=True)

register("OpenAI Compatible", {
    "API Key": env("OPENAI_COMPATIBLE_API_KEY"),
    "Base URL": env("OPENAI_COMPATIBLE_BASE_URL"),
}, supports_embedding=False)

register("OpenRouter", {
    "API Key": env("OPENROUTER_API_KEY"),
    "Base URL": env("OPENROUTER_BASE_URL"),
}, supports_embedding=False)


# ==============================
# PRINT DETECTION
# ==============================
print("=" * 50)
print("DETECTED PROVIDERS (from .env)")
print("=" * 50)
if not PROVIDERS:
    print("  ERROR: No providers with complete credentials!")
    exit(1)

for i, p in enumerate(PROVIDERS):
    emb = "embedding: YES" if p["supports_embedding"] else "embedding: NO"
    print(f"  {i + 1}. {p['name']} ({emb})")
print(f"\nTotal: {len(PROVIDERS)} providers detected")
print("=" * 50)


# ==============================
# ASSIGN ROLES
# ==============================
first_provider = PROVIDERS[0]
second_provider = PROVIDERS[1] if len(PROVIDERS) > 1 else None
embedding_provider = next((p for p in PROVIDERS if p["supports_embedding"]), None)

# Step 2 org provider "Name" / search: all lowercase (uid is already hex lowercase).
org_provider_name = f"{first_provider['name']}-{uid}".lower()
org_provider_description = f"{first_provider['name']} provider for automation".lower()


def fmt(provider):
    lines = f"  Provider Type: {provider['name']}\n"
    for k, v in provider["fields"].items():
        lines += f"    {k}: {v}\n"
    return lines


# ==============================
# MODEL LOGIC
# ==============================
if second_provider:
    model_text = f"""
You have 2 providers. Create 1 model from each (2 models total):
  - Model 1: from "{first_provider['name']}" — pick the first available model
  - Model 2: from "{second_provider['name']}" — pick the first available model

PROVIDER DROPDOWN RULE (CRITICAL):
  - Select providers by exact NAME text from .env, never by list position/index.
  - For Model 2, you MUST select "{second_provider['name']}" specifically.
  - If the dropdown is searchable: clear previous text, type exact provider name, click exact match.
  - After selecting, CLOSE the dropdown (press Escape or click outside), then verify selected value remains visible.

IMPORTANT UI INSTRUCTIONS FOR MODEL CREATION:
  - The Create/Save button is BELOW the visible area inside the modal/dialog
  - After filling in all form fields, you MUST SCROLL DOWN INSIDE THE MODAL to reveal the button
  - Use scroll_down action or scroll within the dialog element
  - Only after the button is visible, click it
  - Wait for confirmation before proceeding"""
else:
    model_text = f"""
You have 1 provider. Create 2 different models from "{first_provider['name']}":
  - Model 1: pick the first available model
  - Model 2: pick a DIFFERENT model from the same provider

IMPORTANT UI INSTRUCTIONS FOR MODEL CREATION:
  - The Create/Save button is BELOW the visible area inside the modal/dialog
  - After filling in all form fields, you MUST SCROLL DOWN INSIDE THE MODAL to reveal the button
  - Use scroll_down action or scroll within the dialog element
  - Only after the button is visible, click it
  - Wait for confirmation before proceeding"""

# ==============================
# EMBEDDING LOGIC
# ==============================
if embedding_provider:
    embedding_text = f"""
Create 1 embedding model from "{embedding_provider['name']}" (supports embeddings):
  - Navigate to Embedding Models section
  - Click Create / Add Embedding Model
  - Select provider: {embedding_provider['name']}
  - Pick the first available embedding model
  - SCROLL DOWN inside the modal/dialog to find the Save/Create button
  - Click Save
"""
else:
    embedding_text = "SKIP — no detected providers support embedding."

# ==============================
# WORKSPACE PROVIDER LOGIC
# ==============================
if second_provider:
    ws_provider_text = f"""
- Navigate to Model Provider section inside the workspace
- Click Create / Add Provider
- Create provider with:
{fmt(second_provider)}
- In any provider dropdown/search, select EXACTLY "{second_provider['name']}" (from .env) — never pick by option order.
- After selecting provider type, close the dropdown (Escape or click outside) before filling the next field.
- SCROLL DOWN inside the modal/dialog if Save/Create button is not visible
- Save and confirm"""
else:
    ws_provider_text = "- SKIP — only 1 provider available. Go to model creation."

# ==============================
# TASK — LOGIN (TC-01) vs POST-LOGIN WORKFLOW
# ==============================
# Login is a separate agent run so we can exit the program if authentication fails
# (wrong credentials, locked account, etc.) without burning steps on the rest of the suite.

TASK_LOGIN = f"""
You execute exactly ONE test case. Do not start any other QA steps after login.

---
TEST CASE ID: TC-01
TITLE: FloTorch Console — user authentication
PRIORITY: P0 (blocking — downstream tests must not run if this fails)
TYPE: Functional / smoke

PRECONDITIONS:
- Valid network access to https://console.flotorch.cloud/
- Test credentials are supplied below (do not ask the user for them).

TEST DATA:
- Email: {email}
- Password: {password}

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

TASK_WORKFLOW = f"""
You are automating a QA workflow on FloTorch. Follow each step in order.
PREREQUISITE: TC-01 (login) already passed in this browser session. You should already be authenticated.
If you are unexpectedly on the login page, use "done" with success=false and explain — do not invent credentials.

Wait for pages to fully load before interacting. After any Save/Create/Submit, wait for success confirmation before continuing.
If a form field doesn't match exactly, use the closest option available in the UI.

CRITICAL RULES FOR ALL FORMS AND MODALS:
1. This application uses modal dialogs (popups) for creating items.
2. The Save/Create/Submit button is ALWAYS at the bottom of the modal — it may be HIDDEN below the visible area.
3. After filling in ALL form fields, SCROLL DOWN INSIDE the modal/dialog to make the button visible.
4. To scroll inside a modal: use the scroll action on the modal element, or press Tab multiple times to reach the button.
5. NEVER skip a step because you cannot find the Create button — it exists, just scroll down to find it.
6. As a last resort, press Tab key repeatedly until the Create/Submit button gets focus, then press Enter.

==============================
STEP 2: CREATE GLOBAL PROVIDER
==============================
- Go to Provider section
- Click Create Organization Provider

Inside the modal:
- In the "Name" field:
   Enter exactly (all lowercase): {org_provider_name}

- In the "Description" field:
   Enter (all lowercase): {org_provider_description}

- In the "Provider" dropdown:
   - Click the Provider dropdown first
   - Search/select ONLY the provider type: {first_provider['name']}
   - Do NOT type {org_provider_name} here
   - Do NOT use the generated provider name in the Provider dropdown

- After selecting the provider type, additional credential fields will appear

- Fill provider credential fields using ONLY the values from {first_provider['fields']}

Rules:
- For each credential field shown in the UI, match its label with the exact key in {first_provider['fields']}
- Enter the corresponding value from {first_provider['fields']} into that field
- Never type placeholder/example values like "test-api-key", "your-api-key", or sample URLs
- Always use the real fetched configuration values

Field mappings:
- "API Key" field → {first_provider['fields'].get('API Key', '')}
- "Base URL" field → {first_provider['fields'].get('Base URL', '')}
- "Region" field → {first_provider['fields'].get('Region', '')}
- "Project ID" field → {first_provider['fields'].get('Project ID', '')}
- "Service Account" field → {first_provider['fields'].get('Service Account', '')}
- "Private Key" field → {first_provider['fields'].get('Private Key', '')}

 -Scroll down inside the modal if needed

- Click "Create Provider"

- After creation, search for {org_provider_name} in the provider search bar and validate it appears in results


==============================
STEP 3: CREATE WORKSPACE
==============================
Primary path:
- Go to Workspace screen
- Click Create / New Workspace
- Name: {workspace_name}
- Description: workspace created by automation run {uid}
- Save and confirm

Failure handling (if create fails, name rejected, quota error, validation error, or workspace does not appear):
- Do not abandon the suite.
- Search or browse the workspace list for an existing workspace named exactly: Default Workspace
- Open that workspace (click it) so you are inside it for later steps.
- On the very next model step after you commit to this fallback, include the exact token {WORKSPACE_FALLBACK_TOKEN} in your "memory" field (required for automation logging).


==============================
STEP 4: ENTER WORKSPACE
==============================
- If Step 3 primary path succeeded: click "{workspace_name}" to open it (use search if many workspaces).
- If Step 3 used the failure path: you should already be inside Default Workspace — if not, open "Default Workspace" from the list.
- Wait for the workspace shell to finish loading before Step 5.

==============================
STEP 5: CREATE 2ND PROVIDER IN WORKSPACE
==============================
{ws_provider_text}

==============================
STEP 6: CREATE MODELS
==============================
{model_text}
- For each: Click Create/Add Model, select provider, pick a model from the list.
- Provider selection must use exact provider name text (from .env), not "2nd item in dropdown".
- After selecting provider in dropdown, close dropdown (Escape or click outside), then continue with model selection.
- SCROLL DOWN inside the modal to find Save/Create button, then click it.

==============================
STEP 7: CREATE EMBEDDING MODEL
==============================
{embedding_text}

==============================
STEP 8: CREATE DATASET
==============================
- Go to Dataset section
- Click Create / New Dataset
- Type: "LLM Evals" (or closest option)
- Name: "llm-evals-{uid}"
- Use sample/default data if available
- SCROLL DOWN inside the modal if needed
- Save

==============================
STEP 9: RUN LLM EVALUATION
==============================
- Go to Evaluations section
- Click "LLM Evaluation"
- Click Create / Run
- Select model(s) from Step 6
- Select embedding model from Step 7 (if created)
- Select dataset "llm-evals-{uid}" from Step 8
- Defaults for everything else
- SCROLL DOWN if needed
- Click Run / Start
- Confirm evaluation started

==============================
FINAL SUMMARY
==============================
Report:
1. Workspace: "{workspace_name}" or "Default Workspace" (if fallback) — status
2. Global Provider: "{org_provider_name}" — status
3. Workspace Provider: "{second_provider['name'] if second_provider else 'SKIPPED'}" — status
4. Models: list each model name + provider
5. Embedding model: name + provider (or skipped)
6. Dataset: "llm-evals-{uid}" — status
7. Evaluation: status
"""


def make_step_end_logger(phase_label: str, *, watch_workspace_fallback: bool = False):
    """Log each browser-use iteration (one LLM step) to stdout — common QA automation visibility."""

    fallback_notice_printed = False

    async def _on_step_end(agent: Agent) -> None:
        nonlocal fallback_notice_printed
        if watch_workspace_fallback and not fallback_notice_printed:
            mo = agent.state.last_model_output
            if mo:
                blob = " ".join(
                    filter(
                        None,
                        [
                            mo.memory,
                            mo.next_goal,
                            mo.evaluation_previous_goal,
                            mo.thinking,
                        ],
                    )
                )
                if WORKSPACE_FALLBACK_TOKEN in blob:
                    print(
                        "\n>>> QA: Custom workspace creation failed — "
                        'continuing inside "Default Workspace".\n'
                    )
                    fallback_notice_printed = True

        completed_idx = max(0, agent.state.n_steps - 1)
        last_url = ""
        if agent.history.history:
            last_url = (agent.history.history[-1].state.url or "").strip()
        url_suffix = f" | {last_url}" if last_url else ""
        print(f"[{phase_label}] browser-use step {completed_idx} finished{url_suffix}")

    return _on_step_end


async def main():
    if not email or not password:
        print("ERROR: FLOTORCH_EMAIL and FLOTORCH_PASSWORD must be set in the environment.")
        raise SystemExit(1)

    llm = ChatGoogle(model="gemini-2.5-flash")

    # 75% zoom: 1920x1080 window renders 2560x1440 worth of content
    # Modals that were cut off will now fit completely on screen
    # keep_alive=True: first Agent.run() must NOT call kill() on this session, or the next Agent
    # can hit "BrowserStateRequestEvent ... none did" (event bus / DOM watchdog out of sync). We kill in `finally` below.
    browser_session = BrowserSession(
        headless=False,
        keep_alive=True,
        window_size={"width": 1920, "height": 1080},
        args=["--force-device-scale-factor=0.75", "--start-maximized"],
    )

    print(f"\nWorkspace: {workspace_name}")
    print(f"Global Provider (name field): {org_provider_name}")
    print(f"Workspace Provider: {second_provider['name'] if second_provider else 'N/A'}")
    print(f"Embedding: {embedding_provider['name'] if embedding_provider else 'N/A'}")
    print(f"Browser: 1920x1080 @ 75% zoom (effective 2560x1440)")
    print("-" * 50)

    try:
        # --- Phase 1: TC-01 Login (hard gate) ---
        print("Phase 1: TC-01 LOGIN (credentials gate)\n")
        login_agent = Agent(
            task=TASK_LOGIN,
            llm=llm,
            browser_session=browser_session,
            max_actions_per_step=5,
            use_vision=True,
            max_failures=4,
        )
        login_history = await login_agent.run(
            max_steps=45,
            on_step_end=make_step_end_logger("TC-01 LOGIN"),
        )

        print("\n" + "=" * 50)
        print("TC-01 LOGIN — phase complete")
        print("=" * 50)
        print(f"  is_done: {login_history.is_done()}")
        print(f"  is_successful: {login_history.is_successful()}")
        if login_history.final_result():
            print(f"  agent final message: {login_history.final_result()}")

        login_ok = login_history.is_done() and login_history.is_successful() is True
        if not login_ok:
            # Guard against false negatives from the LLM login verdict:
            # if the browser is already outside auth pages, continue the suite.
            current_url = ""
            try:
                current_url = (await browser_session.get_current_page_url() or "").lower().strip()
            except Exception:
                current_url = ""

            definitely_still_on_login = (
                "/auth/signin" in current_url
                or "/auth/login" in current_url
                or current_url.endswith("/auth")
            )
            if current_url and not definitely_still_on_login:
                print("\n" + "=" * 50)
                print("LOGIN OVERRIDE: Agent reported failure, but browser appears authenticated.")
                print(f"Current URL after TC-01: {current_url}")
                print("Continuing with Steps 2–9.")
                print("=" * 50)
                login_ok = True

        if not login_ok:
            print("\n" + "=" * 50)
            print("SUITE ABORTED: TC-01 LOGIN did not pass — skipping all downstream steps.")
            print("Fix credentials or account state, then re-run.")
            print("=" * 50)
            out_path = f"result-{uid}.txt"
            with open(out_path, "w", encoding="utf-8") as f:
                f.write("=== TC-01 LOGIN (FAILED OR INCOMPLETE) ===\n")
                f.write(str(login_history))
            print(f"\nSaved login-phase trace to {out_path}")
            return

        # --- Phase 2: full workflow (same browser session) ---
        print("\nPhase 2: post-login QA workflow (Steps 2–9)\n")
        workflow_agent = Agent(
            task=TASK_WORKFLOW,
            llm=llm,
            browser_session=browser_session,
            max_actions_per_step=5,
            use_vision=True,
        )
        result = await workflow_agent.run(
            max_steps=200,
            on_step_end=make_step_end_logger("WORKFLOW", watch_workspace_fallback=True),
        )

        print("\n" + "=" * 50)
        print("AUTOMATION COMPLETE")
        print("=" * 50)
        print(result)

        out_path = f"result-{uid}.txt"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("=== TC-01 LOGIN ===\n")
            f.write(str(login_history))
            f.write("\n\n=== POST-LOGIN WORKFLOW ===\n")
            f.write(str(result))
        print(f"\nSaved full trace to {out_path}")
    finally:
        try:
            await browser_session.kill()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())