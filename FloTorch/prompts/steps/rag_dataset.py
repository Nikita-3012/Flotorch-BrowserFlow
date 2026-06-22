"""STEP 10: RAG dataset (single path)."""

from FloTorch.config.run_context import RunContext
from FloTorch.config.vector_providers import dataset_path_for_vector


def step_rag_datasets(ctx: RunContext) -> str:
    if not ctx.has_vector_rag_path or not ctx.vector_active_path:
        return """
==============================
STEP 10: RAG DATASETS
==============================
SKIP — no vector RAG path. Continue to LLM dataset (Step 11).
"""

    job = ctx.vector_active_path
    if ctx.vector_providers_planned and job.get("use_org_provider"):
        job = {**ctx.vector_providers_planned[0], **ctx.vector_active_path}
    path = dataset_path_for_vector(job)
    name = job.get("rag_dataset_name", "")

    return f"""
==============================
STEP 10: RAG DATASET (one only)
==============================
Create **one** RAG dataset for the active vector path:
- Dataset name (exact): {name}
- Ground truth file: {path}
- Upload flow: Datasets → Create → Q&A Pair → Upload Q&A Pair Files → upload file → Create.
- Verify `{name}` in dataset list.
Do not create RAG datasets for every vector type — only this path.
"""
