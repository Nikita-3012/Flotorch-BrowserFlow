"""STEP 11: LLM dataset creation (shared by LLM and Prompt evaluation)."""

from pathlib import Path

from FloTorch.config.run_context import RunContext

_FLOTORCH_ROOT = Path(__file__).resolve().parent.parent.parent
_GROUND_TRUTH_FILENAME = "llm-dataset.json"


def dataset_ground_truth_path() -> str:
    return str((_FLOTORCH_ROOT / "Dataset" / _GROUND_TRUTH_FILENAME).resolve())


def dataset_name(uid: str) -> str:
    return f"llm-evals-{uid}"


def _dataset_creation_steps(*, dataset_name: str, ground_truth_file: str) -> str:
    return f"""
- Navigate to the Dataset screen (Datasets section in the sidebar).
- Check if any existing dataset is present:
  - If an existing dataset is available, click the Create Dataset button.
  - Otherwise, continue from the initial dataset creation flow.
- On the Choose Dataset Type page, click the Question and Answer Pair section.
- On the Configure Dataset page, click the **Upload Q&A Pair Files** card/tile.
  This step is mandatory — it reveals the hidden file upload element (`<input type="file">`).
  Without clicking this card, the upload action will fail with: "No file upload element found".
- Wait approximately 1 second for the upload section/modal to render completely.
- Enter the dataset name using lowercase and hyphens only (exact): `{dataset_name}`
- Navigate to the Ground Truth File section.
- Click View expected file structure.
- Upload the following JSON file into the Ground Truth File upload section (do not invent JSON in the UI):
  {ground_truth_file}
- Verify that the file upload is completed successfully.
- Click the Create Dataset button.
- Verify that the user is navigated to the Dataset Configure page.
- Click the Back arrow.
- Verify that the dataset row with the name below appears in the dataset list:
  `{dataset_name}`
"""


def build_dataset_text(ctx: RunContext) -> str:
    name = dataset_name(ctx.uid)
    path = dataset_ground_truth_path()
    return f"""
Create ONE LLM dataset only (Steps 12 and 13 reuse it — do NOT create a second dataset for Prompt evaluation):
  - Dataset name (exact): {name}
  - Ground truth file: {path}
{_dataset_creation_steps(dataset_name=name, ground_truth_file=path)}
"""


def step_dataset(ctx: RunContext) -> str:
    return f"""
==============================
STEP 11: CREATE LLM DATASET
==============================
{build_dataset_text(ctx)}
"""
