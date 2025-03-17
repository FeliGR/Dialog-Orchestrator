"""
Flask Extensions Module

This module handles the registration and configuration of Flask extensions used by the
Dialog Orchestrator application. It sets up middleware such as CORS and rate limiting to
ensure the API is secure and resilient.

Extensions are conditionally registered based on the application configuration,
with some being disabled during testing to simplify the test environment.
"""

from flask import Flask
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from adapters.loggers.logger_adapter import app_logger


def register_extensions(app: Flask) -> None:
    """
    Register and initialize Flask extensions for the application.

    This function configures and attaches middleware to the Flask application:
      - CORS: Enables cross-origin requests with configurable origins.
      - Limiter: Adds rate limiting to protect against abuse.

    Args:
        app (Flask): The Flask application instance to register extensions with.
    """
    if not app.config["TESTING"]:
        CORS(
            app,
            resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", "*")}},
        )
        Limiter(
            app=app,
            key_func=get_remote_address,
            default_limits=app.config.get(
                "DEFAULT_RATE_LIMITS", ["100 per day", "10 per minute"]
            ),
        )
    app_logger.debug("Extensions registered")
