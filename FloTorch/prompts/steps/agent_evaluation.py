"""STEP: Agent evaluation — create/publish agent, then run Agent Evaluation in Evaluations."""

from FloTorch.config.run_context import RunContext
from FloTorch.prompts.steps.agent_eval_shared import agent_chat_model_name, agent_dataset_name


def _agent_run_evaluation_block(agent_name: str, agent_dataset: str, model_name: str, ctx: RunContext) -> str:
    return f"""
### RUN AGENT EVALUATION IN EVALUATIONS SECTION

After the agent is created and Published, navigate to the **Evaluations** section to run the Agent Evaluation:

1. Go to **Evaluations** section in the sidebar.
2. Click **Agent Evaluation** (or similar: Create → Agent Evaluation).
3. On the Configuration screen:
   - **Name** (exact, lowercase, hyphens between words — no spaces): agent-evals-run-{ctx.uid}
   - **Agent**: select **{agent_name}** from the dropdown.
   - **Dataset**: select **{agent_dataset}** from the dropdown.
   - **Model / LLM as Judge**: select **{model_name}** from the dropdown.
   - Skip any optional fields.
4. Click **Continue**.
5. On the **Metrics Selection** screen: click **Select All** (or select all available metrics).
6. Click **Next**.
7. On the **Review and Run** screen: click the primary **Run** button.
8. Wait for the success toast / overlay to disappear.
9. Return to the evaluation list and verify **agent-evals-run-{ctx.uid}** appears.
"""


def step_agent_evaluation(ctx: RunContext) -> str:
    if not ctx.has_detected_providers or ctx.first_provider is None:
        return """
==============================
STEP: AGENT EVALUATION
==============================
SKIP — no providers in FloTorch/.env; cannot create agent. Continue to next step.
"""

    model_name = agent_chat_model_name(ctx)
    agent_name = f"agent-evaluation-{ctx.uid}"
    dataset_name = agent_dataset_name(ctx.uid)

    return f"""
==============================
STEP: AGENT EVALUATION — MANUAL WORKSPACE AGENT
==============================
PREREQUISITE: Published chat pipeline **{model_name}** must exist (see `agent_eval_shared.py` or Models phase).
Agent dataset **{dataset_name}** must exist (Datasets phase or already in workspace).
If either is missing, report FAIL and stop.

### AGENT BUILDER FLOW:

1. Navigate to **Agents** menu in the sidebar.
2. Click on **Agent Builder** submenu.
3. Wait for the Agent Builder page to fully load.
4. Click the **"Create FloTorch Agent"** button.
5. Wait for the **Create a FloTorch Agent** popup / modal to be visible.
6. Fill the form:
   - **Name** (exact, lowercase, hyphens between words — no spaces): {agent_name}
   - **Description**: agent created for automation run {ctx.uid}
7. Click **Create** button at the bottom of the modal (scroll inside the modal if not visible).
8. Wait for the Agent configuration page to be visible (should show agent details, model, and publish sections).

### CONFIGURE MODEL:

9. In the **Model** section, click the **+** (plus) icon.
10. Search / typeahead for the pipeline (exact): **{model_name}**
11. Select **{model_name}** from the search results.
12. Click the **"Save Model"** button.
13. Verify the model section shows **{model_name}** as the selected model.

### CONFIGURE AGENT DETAILS:

14. In the **Agent Details** section, click the **+** (plus) icon.
15. Fill the form:
    - **Agent Goal**: Identify the language of the question
16. Click the **"Save Agent Details"** button.
17. Verify the agent details section shows the goal text.

### PUBLISH AGENT:

18. Click the **Publish** button (use the PUBLISH JS from the system message).
19. Wait for the publish dialog to open. Verify it is open using the dialog-detection JS.
20. Set **Summary** to: agent published for automation run {ctx.uid}
21. Check the option **"Mark as latest version once published"**.
22. Click the **Publish** button inside the dialog to confirm.
23. **HARD VERIFICATION:** wait up to 10 seconds for ONE of:
    a) A toast / popup containing "Agent Version Published", "Published successfully", or similar.
    b) The agent page status badge changes to "Published".
    c) The browser navigates back AND the agent row shows "Published".
24. Return to Agent Builder list and verify **{agent_name}** appears with Published status.

{_agent_run_evaluation_block(agent_name=agent_name, agent_dataset=dataset_name, model_name=model_name, ctx=ctx)}
"""
