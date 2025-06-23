"""
Flask Application Factory Module

This module provides a factory pattern implementation for creating and configuring
a Flask application for the Dialog Orchestrator service. It handles the registration
of extensions, use cases, blueprints, error handlers, request hooks, shutdown handlers,
and basic routes.

The ApplicationFactory class ensures consistent application setup with proper
dependency injection and configuration based on the environment.
"""

import os
from typing import Type

from flask import Flask

from adapters.clients.openai_gpt_client import OpenAIGPTClient
from adapters.clients.persona_client import PersonaClient
from adapters.controllers.dialog_controller import create_dialog_blueprint
from adapters.loggers.logger_adapter import app_logger
from app.extensions import register_extensions
from app.handlers import (
    register_error_handlers,
    register_request_hooks,
    register_shutdown_handlers,
)
from app.routes import register_routes
from config import Config, DevelopmentConfig, ProductionConfig, TestingConfig
from usecases.generate_dialog_use_case import GenerateDialogUseCase


class ApplicationFactory:
    """
    Factory class for creating and configuring a Flask application.
    """

    @staticmethod
    def create_app(config_class: Type[Config] = None) -> Flask:
        """
        Creates and configures a Flask application instance.

        Args:
            config_class (Type[Config], optional): The configuration class to use. Defaults to None.

        Returns:
            Flask: The configured Flask application instance.
        """
        if config_class is None:
            env = os.environ.get("FLASK_ENV", "development").lower()
            config_map = {
                "development": DevelopmentConfig,
                "production": ProductionConfig,
                "testing": TestingConfig,
            }
            config_class = config_map.get(env, DevelopmentConfig)

        flask_app = Flask(__name__)
        flask_app.config.from_object(config_class)

        register_extensions(flask_app)
        ApplicationFactory._register_use_cases(flask_app)
        ApplicationFactory._register_blueprints(flask_app)
        register_error_handlers(flask_app)
        register_request_hooks(flask_app)
        register_shutdown_handlers(flask_app)
        register_routes(flask_app)

        app_logger.info(
            "Dialog Orchestrator Application started in %s mode",
            os.environ.get("FLASK_ENV", "development").lower(),
        )
        return flask_app

    @staticmethod
    def _register_use_cases(flask_app: Flask) -> None:
        """
        Registers use cases and attaches them to the Flask app.

        Args:
            flask_app (Flask): The Flask application instance.
        """
        persona_client = PersonaClient()
        gpt_client = OpenAIGPTClient()

        flask_app.generate_dialog_use_case = GenerateDialogUseCase(
            persona_client, gpt_client
        )

    @staticmethod
    def _register_blueprints(flask_app: Flask) -> None:
        """
        Registers blueprints for the Flask application.

        Args:
            flask_app (Flask): The Flask application instance.
        """
        dialog_bp = create_dialog_blueprint(flask_app.generate_dialog_use_case)
        flask_app.register_blueprint(dialog_bp)


create_app = ApplicationFactory.create_app

app = create_app()

if __name__ == "__main__":
    app.run(
        host=app.config.get("HOST", "0.0.0.0"),
        port=app.config.get("PORT", 5002),
        debug=app.config.get("DEBUG", False),
    )
