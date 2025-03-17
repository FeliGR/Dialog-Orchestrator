"""
Persona Client Interface Module

This module defines the interface for the Persona Client adapter.
Any concrete implementation that communicates with the Persona Engine API must
implement the get_persona method to return personality data for a given user ID.
"""

from abc import ABC, abstractmethod


class IPersonaClient(ABC):
    """
    Interface for the Persona Client Adapter.

    This interface specifies the contract for retrieving personality data.
    Implementations must provide a get_persona method that takes a user ID and
    returns a dictionary of personality traits.
    """

    @abstractmethod
    def get_persona(self, user_id: str) -> dict:
        """
        Retrieve the personality data for the given user ID.

        Args:
            user_id (str): The unique identifier for the user.

        Returns:
            dict: A dictionary containing personality traits, for example:
                {
                    "openness": 3,
                    "conscientiousness": 3,
                    "extraversion": 3,
                    "agreeableness": 3,
                    "neuroticism": 3
                }.
        """
