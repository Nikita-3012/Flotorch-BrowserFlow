"""STEP 14: RAG evaluation (single path)."""

from FloTorch.config.run_context import RunContext


def step_rag_evaluations(ctx: RunContext) -> str:
    if not ctx.has_vector_rag_path or not ctx.vector_active_path:
        return """
==============================
STEP 14: RAG EVALUATIONS
==============================
SKIP — no vector storage path for RAG evaluation.
"""

    job = ctx.vector_active_path
    if ctx.vector_providers_planned and job.get("use_org_provider"):
        job = {**ctx.vector_providers_planned[0], **ctx.vector_active_path}
    vs_ref = job.get("provider_ref") or job.get("provider_instance_name", "")
    rag_name = job.get("rag_dataset_name", "")
    eval_name = job.get("rag_eval_name", "")

    return f"""
==============================
STEP 14: RAG EVALUATION (one only)
==============================
- Evaluations → RAG Evaluation
- Name (exact): {eval_name}
- Vector storage: **{vs_ref}**
- Dataset: **{rag_name}** (from Step 10)
- Models / LLM as Judge: prefer Step 6 Published chat models; else Global Model
- Embedding: Step 7 `v1-embedding-{ctx.uid}` if exists
- Metrics → Select All → Next → Run
- Verify `{eval_name}` in evaluation list.
Do not create multiple RAG evaluations for every vector DB — only this path.
"""
