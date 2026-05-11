from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class RunContext:
    uid: str
    workspace_name: str
    email: str
    password: str
    first_provider: dict[str, Any]
    second_provider: dict[str, Any] | None
    selected_second_provider: dict[str, Any] | None
    embedding_provider: dict[str, Any] | None
    org_provider_name: str
    org_provider_description: str
    workspace_second_provider_name: str | None
    workspace_second_provider_description: str | None
