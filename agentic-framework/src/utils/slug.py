"""Module containing slug functionality for the Enterprise Agent Framework."""

import re


def slugify(value: str) -> str:

    """Execute the slugify operation."""
    value = value.strip().lower()

    value = re.sub(
        r"[^a-z0-9]+",
        "_",
        value
    )

    value = re.sub(
        r"_+",
        "_",
        value
    )

    return value.strip("_")