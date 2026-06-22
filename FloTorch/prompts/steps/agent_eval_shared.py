"""Shared helpers for agent and workflow evaluation steps."""

from pathlib import Path

from FloTorch.config.name_slug import name_field_slug
from FloTorch.config.run_context import RunContext

_FLOTORCH_ROOT = Path(__file__).resolve().parent.parent.parent
_AGENT_DATASET_FILE = "agent-1-delete.json"


def _agent_dataset_path() -> str:
    return str((_FLOTORCH_ROOT / "Dataset" / _AGENT_DATASET_FILE).resolve())


def agent_dataset_name(uid: str) -> str:
    return f"agent-dataset-{uid}"


def agent_chat_model_name(ctx: RunContext) -> str:
    if not ctx.has_detected_providers or ctx.first_provider is None:
        return ""
    slug = name_field_slug(ctx.first_provider["name"])
    return f"{slug}-{ctx.uid}"


def workflow_agent1_name(uid: str) -> str:
    return f"agent-evaluation-{uid}"


def create_agent_block(name: str, desc: str, model_name: str, goal: str, system_prompt: str) -> str:
    return f"""
### CREATE AGENT: {name}

1. Navigate to **Agents** → **Agent Builder**.
2. Click **"Create FloTorch Agent"**.
3. Wait for the **Create a FloTorch Agent** popup to be visible.
4. Fill the form:
   - **Name** (exact, lowercase, hyphens between words — no spaces): {name}
   - **Description**: {desc}
5. Click **Create** and wait for the Agent configuration page to load.

### CONFIGURE MODEL ({name}):

6. In the **Model** section, click the **+** icon.
7. Search / typeahead for: **{model_name}**
8. Select **{model_name}** from the results.
9. Click **"Save Model"**.
10. Verify the model section shows **{model_name}**.

### CONFIGURE AGENT DETAILS ({name}):

11. In the **Agent Details** section, click the **+** icon.
12. Fill the form:
    - **Agent Goal**: {goal}
    - **System Prompt**: {system_prompt}
13. Click **"Save Agent Details"**.
14. Verify the agent details section shows the goal text.

### PUBLISH AGENT ({name}):

15. Click the **Publish** button (use the PUBLISH JS from the system message).
16. Wait for the publish dialog → verify open via dialog-detection JS.
17. Set **Summary**: {desc}
18. Check **"Mark as latest version once published"**.
19. Click the **Publish** button inside the dialog.
20. **HARD VERIFICATION:** wait up to 10 seconds for toast "Agent Version Published" / Published badge / agent row Published.
"""


def workflow_agent_create_steps(ctx: RunContext) -> str:
    """Create (or reuse) a single agent before workflow."""
    model_name = agent_chat_model_name(ctx)
    a1 = workflow_agent1_name(ctx.uid)
    agent_eval_ran = "agent" in (ctx.eval_types if ctx.eval_types else [])
    if agent_eval_ran:
        return f"""
### 1. REUSE AGENT (AGENT EVAL ALREADY RAN)

Agent **{a1}** was already created and Published during the Agent Evaluation step.
Verify it exists in Agent Builder list → if found, skip to workflow creation.
If NOT found, create it now:

{create_agent_block(a1, "language identification agent for automation run " + ctx.uid, model_name, "Identify the language of the question", "You are a Language Identification Agent. Identify the language of the input text. Return only the language name.")}
"""
    return f"""
### 1. CREATE AGENT (LANGUAGE IDENTIFICATION)

{create_agent_block(a1, "language identification agent for automation run " + ctx.uid, model_name, "Identify the language of the question", "You are a Language Identification Agent. Identify the language of the input text. Return only the language name.")}
"""


def step_agent_dataset(ctx: RunContext) -> str:
    name = agent_dataset_name(ctx.uid)
    path = _agent_dataset_path()
    return f"""
==============================
STEP: CREATE AGENT / WORKFLOW EVALUATION DATASET
==============================
- Navigate to the **Datasets** screen (Datasets section in the sidebar).
- If an existing dataset is present, click the **Create Dataset** button; otherwise continue from the initial flow.
- On the Choose Dataset Type page, click the **Workflow Evaluation** section (NOT Question and Answer Pair).
- On the Configure Dataset page, click the **Upload Workflow Evaluation File** card / tile.
  This step is mandatory — it reveals the hidden file upload element.
  Without clicking this card, the upload action will fail.
- Wait approximately 1 second for the upload section / modal to render completely.
- Enter the **Name** (exact, lowercase, hyphens between words — no spaces): {name}
- Enter the **Description**: agent workflow evaluation dataset for automation run {ctx.uid}
- Upload the following JSON file into the file upload section (do not invent JSON in the UI):
  {path}
- Verify that the file upload is completed successfully (file name appears after upload).
- Click the **Create Dataset** button.
- Verify that the user is navigated to the Dataset Configure page.
- Click the **Back** arrow.
- Verify that the dataset row with the name below appears in the dataset list:
  {name}
"""
