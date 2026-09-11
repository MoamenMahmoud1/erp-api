from rest_framework.response import Response
from rest_framework.views import exception_handler

from common.exceptions import DomainError


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        return response

    if isinstance(exc, DomainError):
        return Response(
            {"detail": str(exc)},
            status=409,
        )

    return None
