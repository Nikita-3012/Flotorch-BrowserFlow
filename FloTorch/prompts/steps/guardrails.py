"""Guardrails — regression (all types × 4 actions) and sanity (targeted subset)."""

from __future__ import annotations

from FloTorch.config.constants import (
    AWS_BEDROCK_GUARDRAIL_ID,
    AWS_BEDROCK_GUARDRAIL_REPLACE_WITH,
    CUSTOM_GUARDRAIL_KEYWORD_BY_ACTION,
    CUSTOM_GUARDRAIL_KEYWORD_REPLACE_WITH,
    CUSTOM_GUARDRAIL_REGEX_BY_ACTION,
    CUSTOM_GUARDRAIL_REGEX_REPLACE_WITH,
)
from FloTorch.config.run_context import RunContext

GUARDRAIL_ACTIONS: list[tuple[str, str]] = [
    ("Block", "block"),
    ("Redact", "redact"),
    ("Replace", "replace"),
    ("Log", "log"),
]

# AWS Bedrock Add Provider Guardrail
PROVIDER_GUARDRAIL_ACTIONS: list[tuple[str, str]] = [
    ("Block", "block"),
    ("Redact", "redact"),
    ("Replace", "replace"),
    ("Log", "log"),
]


def custom_guardrail_name(uid: str, type_slug: str, action_slug: str) -> str:
    return f"custom-{type_slug}-{action_slug}-{uid}"


def custom_guardrail_description(uid: str, guardrail_type: str, action: str) -> str:
    return f"custom {guardrail_type} guardrail {action} action for run id {uid}"


def provider_guardrail_name(uid: str, action_slug: str) -> str:
    return f"aws-provider-{action_slug}-{uid}"


def ss_guardrail_name(uid: str, action_slug: str) -> str:
    return f"ssn-{action_slug}-{uid}"


def phone_guardrail_name(uid: str, action_slug: str) -> str:
    return f"phone-{action_slug}-{uid}"


def _keyword_specs() -> list[dict[str, str | None]]:
    specs: list[dict[str, str | None]] = []
    for action, slug in GUARDRAIL_ACTIONS:
        replace_with = (
            CUSTOM_GUARDRAIL_KEYWORD_REPLACE_WITH if slug == "replace" else None
        )
        specs.append(
            {
                "action": action,
                "slug": slug,
                "type_slug": "kw",
                "guardrail_type": "Keyword",
                "pattern": CUSTOM_GUARDRAIL_KEYWORD_BY_ACTION[slug],
                "replace_with": replace_with,
            }
        )
    return specs


def _regex_specs() -> list[dict[str, str | None]]:
    specs: list[dict[str, str | None]] = []
    for action, slug in GUARDRAIL_ACTIONS:
        replace_with = (
            CUSTOM_GUARDRAIL_REGEX_REPLACE_WITH if slug == "replace" else None
        )
        specs.append(
            {
                "action": action,
                "slug": slug,
                "type_slug": "regex",
                "guardrail_type": "Regex",
                "pattern": CUSTOM_GUARDRAIL_REGEX_BY_ACTION[slug],
                "replace_with": replace_with,
            }
        )
    return specs


def _pattern_field_label(guardrail_type: str) -> str:
    return "Keyword" if guardrail_type == "Keyword" else "Regex"


def _one_custom_guardrail_block(ctx: RunContext, spec: dict[str, str | None]) -> str:
    action = spec["action"]
    slug = spec["slug"]
    type_slug = spec["type_slug"]
    guardrail_type = spec["guardrail_type"]
    pattern = spec["pattern"]
    replace_with = spec.get("replace_with")
    field_label = _pattern_field_label(guardrail_type)

    name = custom_guardrail_name(ctx.uid, type_slug, slug)
    description = custom_guardrail_description(ctx.uid, guardrail_type, action)

    type_steps = ""
    if guardrail_type == "Regex":
        type_steps = """
   - **Type** dropdown: open and select **Regex** (not Keyword).
"""
    else:
        type_steps = """
   - **Type** dropdown: confirm **Keyword** is selected (default).
"""

    action_steps = f"""
   - **Action** dropdown: select **{action}** (confirm the displayed action is {action}, not a previous selection).
"""
    if replace_with:
        action_steps += f"""
   - After selecting **Replace**, wait until **Replace With** text field is visible.
   - **Replace With** (exact): `{replace_with}`
"""

    return f"""
--- Custom guardrail ({guardrail_type}): Action = **{action}** ---
Name (exact): `{name}`
Description (exact): `{description}`
{type_steps}{action_steps}
   - **{field_label}** (exact): `{pattern}` → click **+** beside the {field_label} field
Click **Create** → wait for **Guardrail created** message → search Repository list for `{name}` → verify row appears.
"""


def _one_provider_guardrail_block(ctx: RunContext, action: str, slug: str) -> str:
    name = provider_guardrail_name(ctx.uid, slug)
    replace_extra = ""
    if slug == "replace":
        replace_extra = f"""
- **Replace With** field (exact): `{AWS_BEDROCK_GUARDRAIL_REPLACE_WITH}`
"""
    return f"""
--- Provider guardrail (AWS Bedrock): Action = **{action}** ---
Name (exact): `{name}`
Description (exact): `provider guardrail {action.lower()} action for run id {ctx.uid}`
- Click **New Guardrail** → **Add Provider Guardrail** (NOT Create Custom Guardrail — **no Type** / Keyword / Regex fields on this form)
- **Provider** dropdown: select the organization provider instance created in Step 2
- **Guardrail** dropdown: select `{AWS_BEDROCK_GUARDRAIL_ID}`
- **Version** dropdown: select latest version (if empty, mark FAIL for this guardrail and continue)
- **Action** dropdown: select **{action}**
{replace_extra}Click **Create** → wait for **Guardrail created** → search Repository for `{name}` → verify row appears.
"""


def _one_ss_guardrail_block(ctx: RunContext, action: str, slug: str) -> str:
    name = ss_guardrail_name(ctx.uid, slug)
    return f"""
--- SS Guardrail: Action = **{action}** ---
Name (exact): `{name}`
- Click **New Guardrail** → **SS Guardrail**
- **Action** dropdown: select **{action}**
Click **Create** → verify row for `{name}` appears in Repository.
"""


def _one_phone_guardrail_block(ctx: RunContext, action: str, slug: str) -> str:
    name = phone_guardrail_name(ctx.uid, slug)
    return f"""
--- Phone Guardrail: Action = **{action}** ---
Name (exact): `{name}`
- Click **New Guardrail** → **Phone Guardrail**
- **Action** dropdown: select **{action}**
Click **Create** → verify row for `{name}` appears in Repository.
"""


def _guardrail_names_list(ctx: RunContext, specs: list[dict[str, str | None]]) -> str:
    return ", ".join(
        f"`{custom_guardrail_name(ctx.uid, s['type_slug'], s['slug'])}`" for s in specs
    )


def all_custom_guardrail_specs() -> list[dict[str, str | None]]:
    return _keyword_specs() + _regex_specs()


def all_custom_guardrail_names(ctx: RunContext) -> list[str]:
    return [
        custom_guardrail_name(ctx.uid, s["type_slug"], s["slug"])
        for s in all_custom_guardrail_specs()
    ]


def all_custom_guardrail_names_bullets(ctx: RunContext) -> str:
    return "\n".join(f"  - `{name}`" for name in all_custom_guardrail_names(ctx))


def all_provider_guardrail_names(ctx: RunContext) -> list[str]:
    return [provider_guardrail_name(ctx.uid, slug) for _, slug in PROVIDER_GUARDRAIL_ACTIONS]


def all_ss_guardrail_names(ctx: RunContext) -> list[str]:
    return [ss_guardrail_name(ctx.uid, slug) for _, slug in GUARDRAIL_ACTIONS]


def all_phone_guardrail_names(ctx: RunContext) -> list[str]:
    return [phone_guardrail_name(ctx.uid, slug) for _, slug in GUARDRAIL_ACTIONS]


def all_regression_guardrail_names(ctx: RunContext, *, include_aws: bool = True) -> list[str]:
    names = all_custom_guardrail_names(ctx)
    if include_aws:
        names.extend(all_provider_guardrail_names(ctx))
    names.extend(all_ss_guardrail_names(ctx))
    names.extend(all_phone_guardrail_names(ctx))
    return names


def all_regression_guardrail_names_bullets(
    ctx: RunContext, *, include_aws: bool = True
) -> str:
    return "\n".join(f"  - `{name}`" for name in all_regression_guardrail_names(ctx, include_aws=include_aws))


def regression_guardrails_catalog_table(
    ctx: RunContext, *, include_aws: bool = True
) -> str:
    """Markdown table of every guardrail the regression create step will create."""
    rows: list[str] = []
    for spec in _keyword_specs():
        rows.append(
            "| Custom | Keyword | "
            f"{spec['action']} | "
            f"`{custom_guardrail_name(ctx.uid, 'kw', spec['slug'])}` | "
            f"`{spec['pattern']}` |"
        )
    for spec in _regex_specs():
        extra = ""
        if spec.get("replace_with"):
            extra = f" → Replace With: `{spec['replace_with']}`"
        rows.append(
            "| Custom | Regex | "
            f"{spec['action']} | "
            f"`{custom_guardrail_name(ctx.uid, 'regex', spec['slug'])}` | "
            f"`{spec['pattern']}`{extra} |"
        )
    if include_aws:
        for action, slug in PROVIDER_GUARDRAIL_ACTIONS:
            extra = ""
            if slug == "replace":
                extra = f"; Replace With: `{AWS_BEDROCK_GUARDRAIL_REPLACE_WITH}`"
            rows.append(
                "| AWS (Provider) | Bedrock | "
                f"{action} | "
                f"`{provider_guardrail_name(ctx.uid, slug)}` | "
                f"`{AWS_BEDROCK_GUARDRAIL_ID}` (latest version{extra}) |"
            )
    else:
        rows.append(
            "| AWS (Provider) | Bedrock | — | — | SKIP (Bedrock not in .env) |"
        )
    for action, slug in GUARDRAIL_ACTIONS:
        rows.append(
            "| SS | SSN | "
            f"{action} | "
            f"`{ss_guardrail_name(ctx.uid, slug)}` | "
            "(platform SS guardrail) |"
        )
    for action, slug in GUARDRAIL_ACTIONS:
        rows.append(
            "| Phone | Phone | "
            f"{action} | "
            f"`{phone_guardrail_name(ctx.uid, slug)}` | "
            "(platform Phone guardrail) |"
        )
    header = (
        "| Category | Type | Action | Name | Pattern / config |\n"
        "|----------|------|--------|------|------------------|"
    )
    return header + "\n" + "\n".join(rows)


def sanity_custom_keyword_replace_name(uid: str) -> str:
    return custom_guardrail_name(uid, "kw", "replace")


def sanity_aws_provider_guardrail_block_name(uid: str) -> str:
    return provider_guardrail_name(uid, "block")


def sanity_ss_guardrail_redact_name(uid: str) -> str:
    return ss_guardrail_name(uid, "redact")


def sanity_phone_guardrail_log_name(uid: str) -> str:
    return phone_guardrail_name(uid, "log")


def pipeline_base_model_from_env(ctx: RunContext) -> str:
    """Instruction for the base-model dropdown when configuring a guardrail test pipeline."""
    if ctx.model_name:
        return (
            f'Select the base model named **"{ctx.model_name}"** from the **FloTorch pipeline model dropdown** '
            f"(exact match to FloTorch/.env — FLOTORCH_MODEL_NAME or the org provider's *_MODEL). "
            f'**"{ctx.model_name}"** is a vendor model id, **not** a website — do **not** navigate to '
            f"`https://{ctx.model_name.split(':')[0].split('/')[0]}` or any URL derived from that string. "
            f"Stay on qa-console.flotorch.cloud; use typeahead in the dropdown only. "
            f"Do **not** pick the first model unless it is **\"{ctx.model_name}\"**."
        )
    provider_label = ctx.first_provider["name"] if ctx.first_provider else "org provider"
    return (
        f"No base model resolved from .env for {provider_label}. "
        "Set **FLOTORCH_MODEL_NAME** or that provider's *_MODEL in FloTorch/.env and re-run. "
        "If you must continue, pick the model that matches your .env intent and report which you chose."
    )


def sanity_output_guardrail_names_bullets(ctx: RunContext) -> str:
    return "\n".join(
        [
            f"  - `{sanity_aws_provider_guardrail_block_name(ctx.uid)}` (AWS Provider Guardrail, action Block)",
        ]
    )


def sanity_final_io_guardrail_names_bullets(ctx: RunContext) -> str:
    return "\n".join(
        [
            f"  - INPUT: `{sanity_ss_guardrail_redact_name(ctx.uid)}` (SS Guardrail, action Redact)",
            f"  - OUTPUT: `{sanity_phone_guardrail_log_name(ctx.uid)}` (Phone Guardrail, action Log)",
        ]
    )


def _repository_create_cycle() -> str:
    return """
ONE-TIME NAVIGATION:
1. Sidebar → **Guardrails** → **Repository** sub-menu.
2. Wait until **Repository** page is fully loaded.

FOR **EACH** guardrail below, repeat this cycle:
A. Click **New Guardrail**.
B. Choose the correct creation path (**Create Custom Guardrail**, **Add Provider Guardrail**, **SS Guardrail**, or **Phone Guardrail**).
C. Fill fields per the block below.
D. Click **Create** → wait for **Guardrail created** validation.
E. Search Repository for the exact name and confirm the row appears.
F. Return to Repository list before the next guardrail.
"""


def _sanity_aws_provider_create_block(ctx: RunContext) -> str:
    aws_name = sanity_aws_provider_guardrail_block_name(ctx.uid)
    if not ctx.guardrail_tests_available:
        return f"""
2) AWS Provider guardrail — SKIP:
- Amazon Bedrock not configured in FloTorch/.env — skip this guardrail.
- Do **not** create `{aws_name}` or any custom guardrail as a substitute for step 2.
- Continue with steps 3 and 4 only.
"""
    return f"""
2) AWS Provider guardrail (Bedrock) — Block:
- Click **New Guardrail** → **Add Provider Guardrail** (NOT **Create Custom Guardrail**).
- Name: `{aws_name}`
- Description: `sanity aws provider guardrail block {ctx.uid}`
- **There is NO Type field** on this form (no Keyword/Regex dropdown — that exists only on Custom guardrails).
- **Provider** dropdown: select the organization provider instance created in Step 2.
- **Guardrail** dropdown: select `{AWS_BEDROCK_GUARDRAIL_ID}`.
- **Version** dropdown: select latest version.
- If Version dropdown is empty, mark FAIL and stop AWS guardrail subtest.
- **Action** dropdown: select **Block** (do **not** use Replace or Redact for this sanity guardrail).
- Click **Create**, then verify repository row for `{aws_name}`.
"""


def step_guardrails_sanity_create(ctx: RunContext) -> str:
    replace_name = sanity_custom_keyword_replace_name(ctx.uid)
    ss_name = sanity_ss_guardrail_redact_name(ctx.uid)
    phone_name = sanity_phone_guardrail_log_name(ctx.uid)
    aws_block = _sanity_aws_provider_create_block(ctx)
    return f"""
==============================
GUARDRAILS SANITY CREATE (TARGETED — EXACTLY 4 GUARDRAILS)
==============================
Create **exactly 4** guardrails — one per category below (or 3 if AWS step is SKIP):

| # | Category | Action | Path |
|---|----------|--------|------|
| 1 | **Custom** (Keyword) | **Replace** | Create Custom Guardrail |
| 2 | **AWS** (Provider/Bedrock) | **Block** | Add Provider Guardrail |
| 3 | **SS** (SSN) | **Redact** | SS Guardrail |
| 4 | **Phone** | **Log** | Phone Guardrail |

1) Custom guardrail — Keyword / Replace:
- Click **New Guardrail** → **Create Custom Guardrail**
- Name: `{replace_name}`
- Description: `sanity custom keyword replace guardrail {ctx.uid}`
- **Type** dropdown: confirm **Keyword** is selected (default).
- **Action** dropdown: select **Replace**
- After selecting **Replace**, wait until **Replace With** is visible.
- **Replace With** (exact): `{CUSTOM_GUARDRAIL_KEYWORD_REPLACE_WITH}`
- **Keyword** field (exact): `{CUSTOM_GUARDRAIL_KEYWORD_BY_ACTION["replace"]}` → click **+** beside the Keyword field
- Click **Create**, then verify repository row for `{replace_name}`.

{aws_block}
3) SS Guardrail — Redact:
- Click **New Guardrail** → **SS Guardrail**
- Name: `{ss_name}`
- **Action** dropdown: select **Redact**
- Click **Create**, then verify row for `{ss_name}`.

4) Phone Guardrail — Log:
- Click **New Guardrail** → **Phone Guardrail**
- Name: `{phone_name}`
- **Action** dropdown: select **Log**
- Click **Create**, then verify row for `{phone_name}`.

NEXT — MODEL CREATION (guardrail test pipeline):
- After guardrails are created, open Model Registry → Models and create the guardrail test model.
- Organization provider: use the instance created in Step 2 (org provider).
- **Base model (from .env):** {pipeline_base_model_from_env(ctx)}
"""


def step_guardrails_regression_create(ctx: RunContext) -> str:
    keyword_specs = _keyword_specs()
    regex_specs = _regex_specs()
    include_aws = ctx.guardrail_tests_available

    keyword_blocks = [_one_custom_guardrail_block(ctx, s) for s in keyword_specs]
    regex_blocks = [_one_custom_guardrail_block(ctx, s) for s in regex_specs]
    provider_blocks = (
        [
            _one_provider_guardrail_block(ctx, action, slug)
            for action, slug in PROVIDER_GUARDRAIL_ACTIONS
        ]
        if include_aws
        else []
    )
    ss_blocks = [_one_ss_guardrail_block(ctx, action, slug) for action, slug in GUARDRAIL_ACTIONS]
    phone_blocks = [
        _one_phone_guardrail_block(ctx, action, slug) for action, slug in GUARDRAIL_ACTIONS
    ]

    custom_count = len(keyword_specs) + len(regex_specs)
    aws_count = len(provider_blocks)
    ss_count = len(ss_blocks)
    phone_count = len(phone_blocks)
    total = custom_count + aws_count + ss_count + phone_count

    aws_part = ""
    if include_aws:
        aws_part = f"""
==============================
PART 3 — AWS PROVIDER GUARDRAILS (4 guardrails)
==============================
- Use **Add Provider Guardrail** for each (not Custom).
- Bedrock guardrail id: `{AWS_BEDROCK_GUARDRAIL_ID}`; Version: latest.
- Actions in order: Block → Redact → Replace (with Replace With `{AWS_BEDROCK_GUARDRAIL_REPLACE_WITH}`) → Log.

{"".join(provider_blocks)}
"""
    else:
        aws_part = """
==============================
PART 3 — AWS PROVIDER GUARDRAILS
==============================
SKIP — Amazon Bedrock not configured in FloTorch/.env. Create Parts 1, 2, 4, and 5 only.
"""

    return f"""
==============================
GUARDRAILS REGRESSION CREATE (ALL TYPES × ALL ACTIONS)
==============================
Create **{total}** guardrails total:
- **Custom** Keyword ×4 + Regex ×4 = {custom_count}
- **AWS Provider** ×3 = {aws_count} {"(skipped — no Bedrock in .env)" if not include_aws else ""} (Block, Redact, Log — no Replace)
- **SS (SSN)** ×4 = {ss_count}
- **Phone** ×4 = {phone_count}

Action order: Custom / SS / Phone use **Block** → **Redact** → **Replace** → **Log**. AWS Provider uses **Block** → **Redact** → **Replace** → **Log**.

CATALOG (create every row):
{regression_guardrails_catalog_table(ctx, include_aws=include_aws)}

{_repository_create_cycle()}

==============================
PART 1 — CUSTOM KEYWORD (4 guardrails)
==============================
- **Type** stays **Keyword** (default) for all four.

{"".join(keyword_blocks)}

==============================
PART 2 — CUSTOM REGEX (4 guardrails)
==============================
- For each: **Type** → **Regex** before entering the pattern.

{"".join(regex_blocks)}
{aws_part}
==============================
PART 4 — SS GUARDRAILS (4 guardrails)
==============================
- Use **SS Guardrail** menu option for each.

{"".join(ss_blocks)}

==============================
PART 5 — PHONE GUARDRAILS (4 guardrails)
==============================
- Use **Phone Guardrail** menu option for each.

{"".join(phone_blocks)}

RULES:
- Create exactly **{total}** guardrails — do not stop after custom-only or after one action.
- Report PASS/FAIL per guardrail (category + action) in memory.
- ALL NAMES THIS RUN:
{all_regression_guardrail_names_bullets(ctx, include_aws=include_aws)}

NEXT — MODEL CREATION:
- **Base model (from .env):** {pipeline_base_model_from_env(ctx)}
"""


def step_custom_guardrail_create(ctx: RunContext) -> str:
    """Backward-compatible alias — regression creates custom + AWS + SS + phone."""
    return step_guardrails_regression_create(ctx)


def step_aws_guardrail_create(ctx: RunContext) -> str:
    if not ctx.guardrail_tests_available:
        return """
==============================
CREATE AWS GUARDRAIL (Bedrock)
==============================
SKIP — Amazon Bedrock org provider not configured in .env.
"""
    blocks = [
        _one_provider_guardrail_block(ctx, action, slug)
        for action, slug in PROVIDER_GUARDRAIL_ACTIONS
    ]
    return f"""
==============================
CREATE AWS PROVIDER GUARDRAILS (3 actions — no Replace)
==============================
{"".join(blocks)}
"""


def step_guardrails_overview(ctx: RunContext) -> str:
    return step_guardrails_regression_create(ctx)
