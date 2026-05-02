"""Yagona JSON xato formati."""
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    detail = response.data
    message = ''
    errors = None

    if isinstance(detail, dict):
        message = str(detail.get('detail') or detail.get('message') or '')
        if not message:
            errors = detail
            message = 'Validation error'
    elif isinstance(detail, list):
        message = str(detail[0]) if detail else 'Error'
    else:
        message = str(detail)

    response.data = {
        'success': False,
        'message': message,
    }
    if errors:
        response.data['errors'] = errors

    return response
