from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from functools import wraps
from jsonview.decorators import json_view
from rest_framework.decorators import api_view
from rest_framework.decorators import authentication_classes
from rest_framework.decorators import permission_classes


def decorator_with_arguments(f):
    """
        A decorator decorator, allowing the decorator to be used as:
        @decorator(with, arguments, and=kwargs)
        or
        @decorator
        http://stackoverflow.com/questions/653368/how-to-create-a-python-decorator-that-can-be-used-either-with-or-without-paramet
    """
    @wraps(f)
    def new_dec(*args, **kwargs):
        if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
            # actual decorated function
            return f(args[0])
        else:
            # decorator arguments
            return lambda realf: f(realf, *args, **kwargs)

    return new_dec


@decorator_with_arguments
def api_exception_logger(func, logger):
    def func_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception('An API exception occurred')
            raise e
    return func_wrapper


def api_endpoint(methods, permissions, logger, auths=()):
    def programmatic_api_endpoint_decorator(func):
        @csrf_exempt
        @api_view(methods)
        @authentication_classes(auths)
        @permission_classes(permissions)
        @json_view
        @api_exception_logger(logger)
        def func_wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return func_wrapper

    def api_endpoint_decorator(func):
        @csrf_exempt
        @api_view(methods)
        @login_required
        @permission_classes(permissions)
        @json_view
        @api_exception_logger(logger)
        def func_wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return func_wrapper

    if len(auths) > 0:
        return programmatic_api_endpoint_decorator
    else:
        return api_endpoint_decorator


def run_if(*args):
    """
    Decorator prevents function run if required feature flag is False and
    raises exception if it doesn't exist.
    """
    feature_flags = args

    def require_settings_decorator(func):
        def wrapper(*args, **kwargs):
            for flag in feature_flags:
                flag_value = getattr(settings, flag, None)
                if not isinstance(flag_value, bool):
                    raise Exception('Setting {} must be either True or '
                                    'False.'.format(flag))
                elif not flag_value:
                    # Don't run the function if the flag is false.
                    return
            return func(*args, **kwargs)
        return wrapper
    return require_settings_decorator
