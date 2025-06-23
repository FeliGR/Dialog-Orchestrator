"""
Dialog Controller Module

This module provides the HTTP controller implementation for the Dialog Orchestrator API.
It handles RESTful operations for generating dialog responses, bridging the HTTP layer
and the application's use cases.
"""

from functools import wraps
from typing import Any, Callable, Dict, Tuple, TypeVar, cast

from flask import Blueprint, jsonify, request
from marshmallow import Schema, ValidationError, fields

from adapters.loggers.logger_adapter import app_logger
from core.interfaces.dialog_controller_interface import IDialogController
from core.interfaces.use_case_interfaces import IGenerateDialogUseCase

ResponseType = Tuple[Dict[str, Any], int]
F = TypeVar("F", bound=Callable[..., ResponseType])


class DialogRequestSchema(Schema):
    """
    Schema for validating the dialog request payload.

    Attributes:
        text (str): The user's input message.
    """

    text = fields.String(required=True)


class ApiResponse:
    """
    Helper class for constructing API responses.
    """

    @staticmethod
    def success(
        data: Any = None, message: str = None, status_code: int = 200
    ) -> ResponseType:
        """
        Create a success response.

        Args:
            data (Any, optional): The response payload.
            message (str, optional): An optional message.
            status_code (int): The HTTP status code.

        Returns:
            ResponseType: A tuple of the JSON response and status code.
        """
        response = {"status": "success"}
        if data is not None:
            response["data"] = data
        if message is not None:
            response["message"] = message
        return jsonify(response), status_code

    @staticmethod
    def error(
        message: str, details: Any = None, status_code: int = 400
    ) -> ResponseType:
        """
        Create an error response.

        Args:
            message (str): The error message.
            details (Any, optional): Additional error details.
            status_code (int): The HTTP status code.

        Returns:
            ResponseType: A tuple of the JSON response and status code.
        """
        response = {"status": "error", "message": message}
        if details is not None:
            response["details"] = details
        return jsonify(response), status_code


def validate_user_id(f: F) -> F:
    """
    Decorator to validate that the user_id parameter is a non-empty string.

    Args:
        f (Callable): The function to decorate.

    Returns:
        Callable: The decorated function.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs) -> ResponseType:
        user_id = kwargs.get("user_id", args[1] if len(args) > 1 else None)
        if not user_id or not isinstance(user_id, str):
            app_logger.error("Invalid user ID: %s", user_id)
            return ApiResponse.error("Invalid user ID", status_code=400)
        return f(*args, **kwargs)

    return cast(F, decorated_function)


class DialogController(IDialogController):
    """
    HTTP controller for handling dialog-related API requests.

    This controller acts as an adapter between the HTTP layer and the dialog generation use case.
    """

    def __init__(self, generate_dialog_uc: IGenerateDialogUseCase):
        """
        Initialize the DialogController.

        Args:
            generate_dialog_uc (IGenerateDialogUseCase):
                The use case for generating dialog responses.
        """
        self.generate_dialog_uc = generate_dialog_uc

    @validate_user_id
    def generate_dialog(self, user_id: str) -> ResponseType:
        """
        Generate a dialog response by combining the user's input with personality data.

        Expects a JSON payload with the following structure:
            {
                "text": "User's input message"
            }

        Args:
            user_id (str): The unique identifier for the user.

        Returns:
            ResponseType: The generated dialog response or an error message.
        """
        try:
            data = request.get_json() or {}
            schema = DialogRequestSchema()
            validated_data = schema.load(data)
            user_text = validated_data["text"]

            app_logger.debug("Executing dialog use case for user_id: %s", user_id)
            bot_response = self.generate_dialog_uc.execute(user_id, user_text)
            return ApiResponse.success({"response": bot_response.text}, status_code=200)
        except ValidationError as err:
            app_logger.error("Validation error: %s", err.messages)
            return ApiResponse.error(
                "Validation error", details=err.messages, status_code=400
            )
        except Exception as e:
            app_logger.error(
                "Error generating dialog for user %s: %s",
                user_id,
                str(e),
                exc_info=True,
            )
            return ApiResponse.error("Internal server error", status_code=500)


def create_dialog_blueprint(generate_dialog_uc: IGenerateDialogUseCase) -> Blueprint:
    """
    Create and configure a Flask blueprint for dialog API endpoints.

    Args:
        generate_dialog_uc (IGenerateDialogUseCase): The use case for generating dialog responses.

    Returns:
        Blueprint: The configured Flask blueprint.
    """
    blueprint = Blueprint("dialog", __name__, url_prefix="/api/dialog")
    controller = DialogController(generate_dialog_uc)

    @blueprint.route("/<string:user_id>", methods=["POST"])
    def generate_dialog(user_id: str):
        return controller.generate_dialog(user_id)

    return blueprint
