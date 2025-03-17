"""
Persona Client Module

This module implements the HTTP client adapter for communicating with the Persona Engine service.
Retrieves personality data for a given user ID by sending a GET request to the Persona Engine API.
"""

import requests

from adapters.loggers.logger_adapter import app_logger
from config import Config
from core.interfaces.persona_client_interface import IPersonaClient


class PersonaClient(IPersonaClient):
    """
    Concrete implementation of the IPersonaClient interface using HTTP requests.
    This client uses the configuration module to determine the base URL for the Persona Engine.
    """

    def __init__(self):
        self.base_url = Config.PERSONA_ENGINE_URL
        app_logger.info("PersonaClient initialized with base URL: %s", self.base_url)

    def get_persona(self, user_id: str) -> dict:
        """
        Retrieve the personality data for a given user ID.

        Args:
            user_id (str): The unique identifier for the user.

        Returns:
            dict: A dictionary containing the personality traits, for example:
                {
                    "openness": 3,
                    "conscientiousness": 3,
                    "extraversion": 3,
                    "agreeableness": 3,
                    "neuroticism": 3
                }.

        Raises:
            Exception: If the HTTP request fails.
        """
        url = f"{self.base_url}/api/persona/{user_id}"
        try:
            app_logger.debug("Requesting persona data from: %s", url)
            response = requests.get(url, timeout=5)  # Timeout set to 5 seconds
            if response.status_code == 200:
                app_logger.info(
                    "Successfully retrieved persona data for user_id: %s", user_id
                )
                return response.json()
            else:
                app_logger.error("Failed to retrieve persona data: %s", response.text)
                return {}
        except Exception as e:
            app_logger.error("Error during persona data retrieval: %s", str(e))
            raise
