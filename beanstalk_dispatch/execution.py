import inspect

from pydoc import locate
from django.conf import settings

from beanstalk_dispatch import ARGS
from beanstalk_dispatch import FUNCTION
from beanstalk_dispatch import KWARGS
from beanstalk_dispatch import BeanstalkDispatchError
from beanstalk_dispatch.safe_task import SafeTask


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
        runnable = locate(function_path)
        if not runnable:
            raise BeanstalkDispatchError(
                'Unable to locate function: {}'.format(function_path))

        args = function_request[ARGS]
        kwargs = function_request[KWARGS]
        if inspect.isclass(runnable):
            if issubclass(runnable, SafeTask):
                task = runnable()
            else:
                raise BeanstalkDispatchError(
                    'Requested task is not a SafeTask subclass: {}'.format(
                        function_request[FUNCTION]))
        else:
            task = SafeTask()
            task.run = runnable
        task.process(*args, **kwargs)
    else:
        raise BeanstalkDispatchError(
            'Requested function not found: {}'.format(
                function_request[FUNCTION]))
