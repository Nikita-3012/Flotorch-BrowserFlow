"""Shared rules for FloTorch UI Name fields: lowercase, hyphens between words, no spaces."""


def name_field_slug(label: str) -> str:
    """Collapse whitespace and underscores to single hyphens; lowercase (for any human-readable label)."""
    return "-".join(label.strip().lower().replace("_", " ").split())


def provider_name_with_uid(provider_display_name: str, uid: str) -> str:
    """Org/workspace provider Name field: slug(provider)-{uid}."""
    return f"{name_field_slug(provider_display_name)}-{uid}"
