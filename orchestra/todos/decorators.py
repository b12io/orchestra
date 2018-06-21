import logging

from django.views.decorators.csrf import csrf_exempt
from jsonview.decorators import json_view
from rest_framework.decorators import api_view
# from rest_framework.decorators import authentication_classes
# from rest_framework.decorators import permission_classes
# from orchestra.todos import IsAssociatedWithProject

logger = logging.getLogger(__name__)


def api_exception_logger(func):
    def func_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception('An API exception occurred')
            raise e
    return func_wrapper


def api_endpoint(methods):
    def api_endpoint_decorator(func):
        @csrf_exempt
        @api_view(methods)
        # @permission_classes((IsAssociatedWithProject,))
        @json_view
        @api_exception_logger
        def func_wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return func_wrapper
    return api_endpoint_decorator
