"""
Dialog Controller Interface Module

This module defines the interface for the Dialog Controller.
Any concrete implementation must implement the generate_dialog method,
which takes a user ID and returns a response tuple (JSON payload and HTTP status code).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple


class IDialogController(ABC):
    """
    Interface for the Dialog Controller.

    This interface specifies the contract for generating dialog responses.
    Implementations must provide a generate_dialog method that accepts a user ID
    and returns a tuple containing the JSON response and HTTP status code.
    """

    @abstractmethod
    def generate_dialog(self, user_id: str) -> Tuple[Dict[str, Any], int]:
        """
        Generate a dialog response for the given user ID.

        Args:
            user_id (str): The unique identifier for the user.

        Returns:
            Tuple[Dict[str, Any], int]: A tuple containing the JSON response and HTTP status code.
        """
