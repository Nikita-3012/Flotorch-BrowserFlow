"""STEP 8: Dataset creation."""

from FloTorch.config.run_context import RunContext


def step_dataset(ctx: RunContext) -> str:
    return f"""
==============================
STEP 8: CREATE DATASET
==============================
- Go to Dataset section
- Click Create / New Dataset
- Type: "LLM Evals" (or closest option)
- Name: "llm-evals-{ctx.uid}"
- Use sample/default data if available
- SCROLL DOWN inside the modal if needed
- Save
"""
