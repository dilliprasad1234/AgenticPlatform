# src/utils/yaml_loader.py

from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from src.exceptions import ValidationError


T = TypeVar("T", bound=BaseModel)


def load_yaml_model(
    path: Path,
    model_type: type[T],
    artifact_name: str,
) -> T:

    try:
        with open(
            path,
            "r",
            encoding="utf-8",
        ) as f:
            data = yaml.safe_load(f)

        return model_type.model_validate(data)

    except (
        OSError,
        yaml.YAMLError,
        PydanticValidationError,
    ) as exc:

        raise ValidationError(
            f"Invalid {artifact_name}.",
            user_message=(
                f"{artifact_name} is invalid."
            ),
        ) from exc