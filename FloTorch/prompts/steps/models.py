"""STEP 6–7: Chat models and embedding model."""

from FloTorch.config.run_context import RunContext


def build_chat_models_text(ctx: RunContext) -> str:
    first = ctx.first_provider
    second = ctx.selected_second_provider
    if second:
        return f"""
You have 2 providers. Create 1 model from each (2 models total):
  - Model 1: from "{first['name']}" — pick the first available model
  - Model 2: from "{second['name']}" — pick the first available model
  - Use model names:
    - First model name: v1
    - Second model name: v2

PROVIDER DROPDOWN RULE (CRITICAL):
  - Select providers by exact NAME text from .env, never by list position/index.
  - For Model 2, you MUST select "{second['name']}" specifically.
  - Assume NO search is available in this dropdown.
  - Scroll inside the dropdown list until the exact option title is visible, then click the exact title row.
  - Do NOT click description text/subtext under an option.
  - After selecting the provider option, CLOSE the dropdown by clicking an empty area in the modal (preferred).
    Use Escape ONLY if clicking outside does not close it.
  - HARD VERIFICATION (MANDATORY): the dropdown list must be closed AND the provider field must display exactly the selected provider name.
    If it doesn't stick, reopen the dropdown and repeat (up to 3 attempts) before continuing.

IMPORTANT UI INSTRUCTIONS FOR MODEL CREATION:
  - Click "Create FloTorch Model" to open the model modal
  - Fill Name and Description fields (Description should be meaningful, not secrets)
  - For normal models, keep Type as default "Chat"
  - Click Create button
  - Wait a few seconds for the next screen/list refresh before starting the next model
  - The Create/Save button is BELOW the visible area inside the modal/dialog
  - After filling in all form fields, you MUST SCROLL DOWN INSIDE THE MODAL to reveal the button
  - Use scroll_down action or scroll within the dialog element
  - Only after the button is visible, click it
  - Wait for confirmation before proceeding"""
    return f"""
You have 1 provider. Create 2 different models from "{first['name']}":
  - Model 1: pick the first available model
  - Model 2: pick a DIFFERENT model from the same provider
  - Use model names:
    - First model name: v1
    - Second model name: v2

IMPORTANT UI INSTRUCTIONS FOR MODEL CREATION:
  - Click "Create FloTorch Model" to open the model modal
  - Fill Name and Description fields (Description should be meaningful, not secrets)
  - For normal models, keep Type as default "Chat"
  - Click Create button
  - Wait a few seconds for the next screen/list refresh before starting the next model
  - The Create/Save button is BELOW the visible area inside the modal/dialog
  - After filling in all form fields, you MUST SCROLL DOWN INSIDE THE MODAL to reveal the button
  - Use scroll_down action or scroll within the dialog element
  - Only after the button is visible, click it
  - Wait for confirmation before proceeding"""


def build_embedding_text(ctx: RunContext) -> str:
    ep = ctx.embedding_provider
    if not ep:
        return "SKIP — no detected providers support embedding."
    return f"""
Create 1 embedding model from "{ep['name']}" (supports embeddings):
  - Navigate to Models section under the 'Model Registry' Menu
  - Click "Create FloTorch Model"
  - Name: v1-embedding-{ctx.uid}
  - Description: embedding model for automation run {ctx.uid}
  - Type: change from "Chat" to "Embedding"
  - Select provider: {ep['name']}
  - Pick the first available embedding model
  - SCROLL DOWN inside the modal/dialog to find the Save/Create button
  - Click Create
  - Wait a few seconds for the new screen/list to load
"""


def step_chat_models(ctx: RunContext) -> str:
    model_text = build_chat_models_text(ctx)
    return f"""
==============================
STEP 6: CREATE MODELS
==============================
{model_text}
- For each: Click Create/Add Model, select provider, pick a model from the list.
- Provider selection must use exact provider name text (from .env), not "2nd item in dropdown".
- After selecting provider in dropdown, close dropdown (Escape or click outside), then continue with model selection.
- SCROLL DOWN inside the modal to find Save/Create button, then click it.
"""


def step_embedding_model(ctx: RunContext) -> str:
    embedding_text = build_embedding_text(ctx)
    return f"""
==============================
STEP 7: CREATE EMBEDDING MODEL
==============================
{embedding_text}
"""
