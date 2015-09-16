# TODO(marcua): Change this module name from `settings` to something else.
# Especially since we import django settings here, we're bound to run into
# some naming conflict or confusion.
from django.conf import settings


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
