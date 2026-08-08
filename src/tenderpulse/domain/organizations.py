from __future__ import annotations

import unicodedata


def display_organization_name(value: str) -> str:
    """Preserve the source spelling while removing insignificant outer whitespace."""
    display = " ".join(value.split())
    if not display:
        raise ValueError("organization name cannot be empty")
    return display


def normalize_organization_name(value: str) -> str:
    """Produce a conservative comparison key without stripping legal forms."""
    display = display_organization_name(unicodedata.normalize("NFKC", value))
    characters = (character.casefold() if character.isalnum() else " " for character in display)
    normalized = " ".join("".join(characters).split())
    if not normalized:
        raise ValueError("organization name has no letters or numbers")
    return normalized
