"""Yagona JSON xato formati."""
import logging

from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


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

    # 400 xatolarni debug uchun logga yozamiz (request body bilan)
    if response.status_code == 400:
        request = context.get('request') if context else None
        view = context.get('view') if context else None
        try:
            body = getattr(request, 'data', None)
        except Exception:  # noqa: BLE001
            body = '<unreadable>'
        logger.warning(
            'Validation 400 in %s: errors=%s | body=%s',
            getattr(view, '__class__', type('?', (), {})).__name__,
            errors or message,
            body,
        )

    response.data = {
        'success': False,
        'message': message,
    }
    if errors:
        response.data['errors'] = errors

    return response
