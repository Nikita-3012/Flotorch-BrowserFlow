"""STEP: Workflow evaluation — agents, workflow canvas, publish, then Workflow Evaluation in Evaluations."""



from FloTorch.config.run_context import RunContext

from FloTorch.prompts.steps.agent_eval_shared import (

    agent_chat_model_name,

    agent_dataset_name,

    workflow_agent1_name,

    workflow_agent_create_steps,

)





def _workflow_run_evaluation_block(workflow_name: str, agent_dataset: str, model_name: str, ctx: RunContext) -> str:

    return f"""

### RUN WORKFLOW EVALUATION IN EVALUATIONS SECTION



After the workflow is created and Published, navigate to the **Evaluations** section to run the Workflow Evaluation:



1. Go to **Evaluations** section in the sidebar.

2. Click **Workflow Evaluation** (or Create → Workflow Evaluation).

3. On the Configuration screen:

   - **Name** (exact, lowercase, hyphens between words — no spaces): workflow-evals-run-{ctx.uid}

   - **Workflow**: select **{workflow_name}** from the dropdown.

   - **Dataset**: select **{agent_dataset}** from the dropdown.

   - **Model / LLM as Judge**: select **{model_name}** from the dropdown.

   - Skip any optional fields.

4. Click **Continue**.

5. On the **Metrics Selection** screen: click **Select All** (or select all available metrics).

6. Click **Next**.

7. On the **Review and Run** screen: click the primary **Run** button.

8. Wait for the success toast / overlay to disappear.

9. Return to the evaluation list and verify **workflow-evals-run-{ctx.uid}** appears.

"""





def step_workflow_evaluation(ctx: RunContext) -> str:

    if not ctx.has_detected_providers or ctx.first_provider is None:

        return """

==============================

STEP: WORKFLOW EVALUATION

==============================

SKIP — no providers in FloTorch/.env; cannot create workflow. Continue to next step.

"""



    model_name = agent_chat_model_name(ctx)

    agent1_name = workflow_agent1_name(ctx.uid)

    workflow_name = f"workflow-evaluation-{ctx.uid}"

    dataset_name = agent_dataset_name(ctx.uid)

    agent_steps = workflow_agent_create_steps(ctx)



    return f"""

==============================

STEP: WORKFLOW EVALUATION

==============================

PREREQUISITE: Published chat pipeline **{model_name}** must exist (see `agent_eval_shared.py`).

Agent dataset **{dataset_name}** must exist.

Agent **{agent1_name}** must already exist when `WORKFLOW_CREATE_AGENTS = False`.

(No second agent is required for this workflow.)



EXECUTION ORDER (strict — complete each block before the next):

§3 Create workflow → §4 Add agent → §6 Connect edges (drag black→red) → §7 Publish → run workflow evaluation.



Do **NOT** open Agent Builder when agent steps are skipped — go to **§3 CREATE WORKFLOW**.

Do **NOT** call `done` with success=false while still on the workflow canvas — finish §6–§7 first.

**AGENT CONFIGURATION POPUP (canvas — mandatory):**
- While adding agents or moving nodes on the workflow canvas, **Agent Configuration** may open if you click a node body by mistake.
- **Always close it immediately:** click **Close** or **X** on the modal — do **not** save or edit fields inside it.
- After closing, continue the current step (add agent, separate nodes, or connect edges).



---



{agent_steps}### 3. CREATE WORKFLOW



1. Navigate to **Agents** → **Workflow** submenu (NOT Agent Builder).

2. Click **"Create FloTorch Workflow"** button.

3. Wait for the **Create a FloTorch Workflow** popup to be visible.

4. Fill the form:

   - **Name** (exact, lowercase, hyphens between words — no spaces): {workflow_name}

   - **Description**: workflow evaluation for automation run {ctx.uid}

5. Click **Create** button.

6. Wait for the success popup / toast to be visible and dismiss it.

7. Wait for the Workflow canvas / builder page to fully load.



---



### 4. ADD AGENT TO WORKFLOW

**While adding the agent node:** if **Agent Configuration** opens at any point, click **Close** / **X** right away — do not save — then continue this section.

1. Click the **"Add Agent"** button on the workflow canvas.

2. Search for agent: **{agent1_name}**

3. Tick / check the checkbox next to **{agent1_name}** in the search results.

4. Click the **"Add Agents"** button to add the selected agent to the canvas.

5. Dismiss any success toast (e.g. "Agents added to workflow").

6. **If Agent Configuration opened** after adding the agent, click **Close** / **X** — do not save.

7. Confirm all three nodes are on the canvas: **Start**, **{agent1_name}**, **End**.

8. If nodes overlap, **`drag`** node borders (not ports) to separate them so **Start**, **{agent1_name}**, and **End** are visible left-to-right with space between ports.
   - **If Agent Configuration opens while dragging a node**, click **Close** / **X** immediately, then resume separating nodes.

9. Before connecting edges, verify **Agent Configuration** is closed. If still open, click **Close** / **X**.

10. Proceed immediately to **§6 CONNECT EDGES** — connect Start → agent → End using the black/red dots.



---



### 6. CONNECT EDGES (DRAG BLACK DOT → RED DOT — ONE PASS ONLY)



After the agent is on the canvas, connect exactly **2 edges** once using **`drag`**, then go to §7.

**Never** use `evaluate`, JavaScript, XPath, or CSS.



Each node has two colored connector dots on its sides:

- **Black / dark dot** = output / source port (on the **right** side of **Start** and **{agent1_name}**)

- **Red dot** = input / target port (on the **left** side of **{agent1_name}** and **End**)



**Setup:** dismiss all toasts. Close **Agent Configuration** modal if open (click **Close** / **X**).



**Connect in order — click the black dot, then drag to the red dot (2 drags total):**



1. **Start → {agent1_name}:** click the **black dot** on the **right** side of the **Start** node, then **`drag`** to the **red dot** on the **left** side of **{agent1_name}**.

2. **{agent1_name} → End:** click the **black dot** on the **right** side of **{agent1_name}**, then **`drag`** to the **red dot** on the **left** side of the **End** node.



**HARD RULE — target only the colored dots:**

- Hover carefully and interact ONLY with the small black/red port circles — not the node body.

- If you click the node body by mistake, **Agent Configuration** opens → click **Close** / **X** immediately, then retry that edge from the black dot.



**Fallback:** if drag does not draw an edge, use two **`click`** actions per pair (black dot on source, then red dot on target) for the same 2 connections.



**After every action:** if **Agent Configuration** opens, click **Close** immediately — do not save.



**Toasts (do not retry the same pair):**

- **Edge already exists** → that pair is done; continue to the next pair or §7.

- Do **not** re-draw edges that are already visible on the canvas.



**If toast says cycle / invalid workflow:** click a duplicate edge line, press **Delete** / **Backspace**, remove extras until at most 2 edges remain, then go to **§7** — do **not** reconnect all edges again.



**Leave §6 when:** 2 edges are visible **or** both pairs returned **Edge already exists** → **immediately** proceed to §7.



---



### 7. PUBLISH WORKFLOW



1. Click the **Publish** button in the workflow toolbar.

2. Wait for the publish dialog to open. Verify it is open using the dialog-detection JS from the system message.

3. Set the **Summary** to: workflow published for automation run {ctx.uid}

4. Check the option **"Mark as latest version once published"**.

5. Click the **Publish** button inside the dialog to confirm.

6. **HARD VERIFICATION:** wait up to 10 seconds and verify TWO success messages appear:

   - "Workflow Version Published" (or similar) toast / popup.

   - The workflow page status badge changes to **Published**.



If Publish does not open the dialog **once**: separate overlapping nodes on the canvas, then **§6** for any missing edge only, and retry **Publish** once. Do **not** enter a reconnect loop.



{_workflow_run_evaluation_block(workflow_name=workflow_name, agent_dataset=dataset_name, model_name=model_name, ctx=ctx)}

"""


