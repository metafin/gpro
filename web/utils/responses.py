"""API response helper functions."""
from flask import jsonify


def success_response(data=None, message=None):
    """Return a successful API response."""
    response = {"status": "ok"}
    if data is not None:
        response["data"] = data
    if message is not None:
        response["message"] = message
    return jsonify(response), 200


def error_response(message, status_code=400):
    """Return an error API response."""
    return jsonify({"status": "error", "message": message}), status_code


def validation_response(errors):
    """Return a validation result response."""
    return jsonify({"valid": len(errors) == 0, "errors": errors}), 200
