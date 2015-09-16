from beanstalk_dispatch import ARGS
from beanstalk_dispatch import FUNCTION
from beanstalk_dispatch import KWARGS
from beanstalk_dispatch import BeanstalkDispatchError
from django.conf import settings
from importlib import import_module


def execute_function(function_request):
    """
    Given a request created by
    `beanstalk_dispatch.common.create_request_body`, executes the
    request.  This function is to be run on a beanstalk worker.
    """
    dispatch_table = getattr(settings, 'BEANSTALK_DISPATCH_TABLE', None)

    if dispatch_table is None:
        raise BeanstalkDispatchError('No beanstalk dispatch table configured')
    for key in (FUNCTION, ARGS, KWARGS):
        if key not in function_request.keys():
            raise BeanstalkDispatchError(
                'Please provide a {} argument'.format(key))

    module_name, function_name = (
        dispatch_table.get(function_request[FUNCTION], (None, None)))
    if module_name and function_name:
        # TODO(marcua): Catch import errors and rethrow them as
        # BeanstalkDispatchErrors.
        module = import_module(module_name)
        function = getattr(module, function_name)
        function(*function_request[ARGS], **function_request[KWARGS])
    else:
        raise BeanstalkDispatchError(
            'Requested function not found: {}'.format(
                function_request[FUNCTION]))
