"""Shared API error response helpers.

Successful endpoints intentionally keep their existing payloads. This module
only defines the stable shape used by every JSON error response.
"""

from flask import jsonify


AUTH_INVALID_CREDENTIALS = 'AUTH_INVALID_CREDENTIALS'
AUTH_REQUIRED = 'AUTH_REQUIRED'
AUTH_TOKEN_EXPIRED = 'AUTH_TOKEN_EXPIRED'
AUTH_INVALID_TOKEN = 'AUTH_INVALID_TOKEN'
VALIDATION_ERROR = 'VALIDATION_ERROR'
FORBIDDEN = 'FORBIDDEN'
NOT_FOUND = 'NOT_FOUND'
CONFLICT = 'CONFLICT'
PAYLOAD_TOO_LARGE = 'PAYLOAD_TOO_LARGE'
FEATURE_DISABLED = 'FEATURE_DISABLED'
INTERNAL_ERROR = 'INTERNAL_ERROR'
METHOD_NOT_ALLOWED = 'METHOD_NOT_ALLOWED'

DEFAULT_ERROR_CODES = {
    400: VALIDATION_ERROR,
    401: AUTH_REQUIRED,
    403: FORBIDDEN,
    404: NOT_FOUND,
    405: METHOD_NOT_ALLOWED,
    409: CONFLICT,
    413: PAYLOAD_TOO_LARGE,
    500: INTERNAL_ERROR,
    503: FEATURE_DISABLED,
}


def error_code_for_status(status_code):
    """Return the standard business code for an HTTP failure status."""
    return DEFAULT_ERROR_CODES.get(
        status_code,
        INTERNAL_ERROR if status_code >= 500 else VALIDATION_ERROR,
    )


def error_response(code, message, status_code):
    return jsonify({'code': code, 'message': message}), status_code
