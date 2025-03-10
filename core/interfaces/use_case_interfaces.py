"""
Use Case Interfaces Module

This module defines the interfaces for use cases within the Dialog Orchestrator application.
These interfaces establish the contract that concrete use case implementations must follow,
ensuring consistency and separation of concerns across the application.
"""

from abc import ABC, abstractmethod

from core.domain.dialog_model import BotResponse


class IGenerateDialogUseCase(ABC):
    """
    Interface for the Generate Dialog Use Case.

    This interface defines the contract for generating a dialog response by integrating
    personality data with the user's input. Implementations must provide the execute method
    that returns a BotResponse based on the provided user ID and input message.
    """

    @abstractmethod
    def execute(self, user_id: str, user_text: str) -> BotResponse:
        """
        Execute the dialog generation use case.

        Args:
            user_id (str): The unique identifier for the user.
            user_text (str): The text input provided by the user.

        Returns:
            BotResponse: The generated response from the language model.
        """
