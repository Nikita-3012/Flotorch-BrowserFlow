"""
FloTorch QA Automation — Execution Plan
========================================

MODULES = "all"  →  run TEST CASES (in order):
                      guardrails → prompt_partials → evaluations (only if EVAL_TYPES set)

Preconditions (org provider, workspace, models, datasets, etc.) are created
automatically before test cases when needed — you do not list them in MODULES.

EVAL_TYPES:
  [] or empty     →  no evaluations test case (guardrails + prompt_partials only)
  ["llm"]         →  run llm evaluation (+ its preconditions)
  ["agent", ...]  →  run those evaluations (+ merged preconditions)
  "all"           →  all five evaluation types
"""

# ===== EVALUATION TYPES =====
# Empty = skip evaluations (guardrails + prompt_partials only when MODULES=all)
# EVAL_TYPES = []
# EVAL_TYPES = ["llm"]
# EVAL_TYPES = ["agent", "workflow"]
# EVAL_TYPES = "all"
EVAL_TYPES = []

# ===== MODULES =====
# "all" → guardrails + prompt_partials + evaluations (if EVAL_TYPES non-empty)
MODULES = "prompt_partials"
