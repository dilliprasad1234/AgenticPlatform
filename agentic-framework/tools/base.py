"""Module containing base functionality for the Enterprise Agent Framework."""

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """
    Base class for all framework tools.
    """

    @abstractmethod
    def execute(self, **kwargs: Any) -> Any:
        """
        Execute the tool.
        """
        raise NotImplementedError