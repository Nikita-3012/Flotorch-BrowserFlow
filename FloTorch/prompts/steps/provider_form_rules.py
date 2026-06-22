"""Shared provider modal rules (Service multi-select)."""


def provider_service_select_all() -> str:
    """FloTorch org/workspace provider modals use a Service dropdown (no separate Type dropdown)."""
    return """
PROVIDER MODAL — SERVICE DROPDOWN (MANDATORY on org and workspace provider creates):
- FloTorch does **not** use a separate "Type" dropdown on these forms — only **Service** (may be labeled "Service", "Services", or "Service Type").
- Do **not** look for a "Type" field; if you only see Service, that is correct.
- After choosing the **Provider** (vendor) dropdown, open **Service** and **tick/check EVERY Service option** (multi-select).
  - Scroll inside the Service overlay/listbox; click each row until **all** options show a checkmark/tick.
  - If "Select All" or "All" exists, use it; otherwise select each Service option one by one.
  - Re-open and fix if any Service row lacks a tick before closing the dropdown.
- Enter API keys / credentials **only after** all Service options are ticked.
- **Close the Service dropdown:** click **outside** the dropdown panel (neutral area inside the modal, e.g. Name/Description label area) — **not** the modal X/backdrop — until the Service list is fully closed.
- HARD GATE: do not click Create/Save until every Service option is selected and the Service dropdown is closed.
"""


# Backward-compatible alias used across prompts
def provider_service_and_type_select_all() -> str:
    return provider_service_select_all()
