"""
Dialog Domain Service Interface Module

This module defines the IDialogDomainService interface for composing dialog prompts.
It integrates personality data with user input to generate prompts for the language model.
"""

from abc import ABC, abstractmethod
from typing import Dict


class IDialogDomainService(ABC):
    """
    Dialog Domain Service Interface.

    This interface defines the contract for the domain service responsible for composing
    dialog prompts by integrating personality data with user input.
    """

    @abstractmethod
    def compose_prompt(self, persona_data: Dict[str, float], user_text: str) -> str:
        """
        Compose a prompt that integrates personality data with the user's input.

        Args:
            persona_data (Dict[str, float]): A dictionary containing personality traits,
                for example: {"extraversion": 4.5, "agreeableness": 3.5, ...}.
            user_text (str): The text provided by the user.

        Returns:
            str: The composed prompt to be sent to the language model.
        """
        pass
