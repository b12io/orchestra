from pydoc import locate
from django.conf import settings

from beanstalk_dispatch import ARGS
from beanstalk_dispatch import FUNCTION
from beanstalk_dispatch import KWARGS
from beanstalk_dispatch import BeanstalkDispatchError


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

    function_path = dispatch_table.get(
        function_request[FUNCTION], ''
    )

    if function_path:
        # TODO(marcua): Catch import errors and rethrow them as
        # BeanstalkDispatchErrors.
        function = locate(function_path)
        function(*function_request[ARGS], **function_request[KWARGS])
    else:
        raise BeanstalkDispatchError(
            'Requested function not found: {}'.format(
                function_request[FUNCTION]))
