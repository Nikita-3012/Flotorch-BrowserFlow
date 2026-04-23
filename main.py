from browser_use import Agent, Browser, ChatGoogle
from dotenv import load_dotenv
import os
import asyncio
import uuid

load_dotenv()

# FloTorch credentials
email = os.getenv("FLOTORCH_EMAIL")
password = os.getenv("FLOTORCH_PASSWORD")

# Groq
groq_api_key = os.getenv("GROQ_API_KEY", "")

# Google Generative AI (Gemini)
google_genai_key = os.getenv("GOOGLE_API_KEY", "")

# Google Vertex AI
google_vertex_project = os.getenv("GOOGLE_VERTEX_PROJECT_ID", "")
google_vertex_region = os.getenv("GOOGLE_VERTEX_REGION", "us-central1")
google_vertex_creds = os.getenv("GOOGLE_VERTEX_CREDENTIALS_PATH", "")

# Unique ID for naming
uid = uuid.uuid4().hex[:6]
workspace_name = f"Automation-{uid}"

task = f"""
You are automating a full QA workflow on FloTorch. Follow every step carefully.
Always wait for pages to fully load. After clicking Save/Create/Submit, wait for confirmation before proceeding.

==============================
STEP 1: LOGIN
==============================
- Go to https://qa-console.flotorch.cloud/
- Enter email: {email}
- Enter password: {password}
- Click Login
- Wait for dashboard to fully load

==============================
STEP 2: CREATE WORKSPACE
==============================
- Navigate to the Workspace section
- Click Create / New Workspace
- Select "Automation" type if there's a type selection
- Name it: {workspace_name}
- Save/Create it
- Confirm it appears in the workspace list

==============================
STEP 3: ENTER WORKSPACE
==============================
- Click on "{workspace_name}" to enter it
- Wait for workspace dashboard to load

==============================
STEP 4: CREATE MODEL PROVIDERS
==============================
Navigate to the Model Provider section. Create these 3 providers one by one:

--- Provider 1: Groq ---
- Type: Groq
- API Key: {groq_api_key}
- Save and confirm

--- Provider 2: Google Generative AI (Gemini) ---
- Type: Google Generative AI / Google AI / Gemini (whatever the UI calls it)
- API Key: {google_genai_key}
- Save and confirm

--- Provider 3: Google Vertex AI ---
- Type: Google Vertex AI
- Project ID: {google_vertex_project}
- Region: {google_vertex_region}
- Credentials/Service Account: {google_vertex_creds} (if asked)
- Save and confirm

If any credential is empty or blank, SKIP that provider entirely.

==============================
STEP 5: CREATE MODELS
==============================
For EACH provider created in Step 4:
- Go to Models section (or Add Model within the provider)
- Click Create / Add Model
- The UI should list available models for that provider
- Pick the first available or recommended model
- Save it
- Repeat for all providers

==============================
STEP 6: CREATE EMBEDDING MODELS
==============================
IMPORTANT: Not all providers support embedding models.

- Groq: NO — does NOT support embedding models. SKIP Groq.
- Google Generative AI: YES — supports embedding (e.g., embedding-001, text-embedding-004)
- Google Vertex AI: YES — supports embedding (e.g., textembedding-gecko)

For each embedding-supported provider (Google GenAI and Google Vertex only):
- Navigate to Embedding Models section
- Click Create / Add Embedding Model
- Select the provider
- Pick an available embedding model from the dropdown/list
- Save it

If the UI does not show embedding options for a provider, skip it.

==============================
STEP 7: CREATE DATASET
==============================
- Navigate to the Dataset section (for LLM Evals)
- Click Create / Add / New Dataset
- If there is a "Sample" or "Default" dataset option, use that
- If you need to name it: "eval-dataset-{uid}"
- Save the dataset

==============================
STEP 8: CREATE EVALUATION
==============================
- Navigate to the Evaluations section
- Click Create / New Evaluation
- Fill in the form:
    - Name: "eval-run-{uid}"
    - Select the model(s) created in Step 5
    - Select the embedding model(s) created in Step 6
    - Select the dataset created in Step 7
    - Use default/recommended values for any other settings
- Create / Start the evaluation
- Confirm it was created successfully

==============================
FINAL SUMMARY
==============================
After all steps, report back:
1. Workspace created: name and status
2. Providers created (list which ones, and which were skipped)
3. Models created per provider (name of each model)
4. Embedding models created (name of each, and which providers were skipped)
5. Dataset name and status
6. Evaluation name and status
"""


async def main():
    llm = ChatGoogle(model="gemini-2.5-flash")

    browser = Browser(
        headless=False,
    )

    agent = Agent(
        task=task,
        llm=llm,
        browser=browser,
        max_actions_per_step=5,
    )

    print(f"Starting automation...")
    print(f"Workspace name: {workspace_name}")
    print(f"Unique ID: {uid}")
    print("-" * 50)

    result = await agent.run(max_steps=200)

    print("\n" + "=" * 50)
    print("AUTOMATION COMPLETE")
    print("=" * 50)
    print(result)

    # Save result to file
    with open(f"result-{uid}.txt", "w", encoding="utf-8") as f:
        f.write(str(result))
    print(f"\nResult saved to result-{uid}.txt")


if __name__ == "__main__":
    asyncio.run(main())

