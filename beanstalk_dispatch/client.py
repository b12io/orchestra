import boto.sqs

from beanstalk_dispatch.common import create_request_body
from django.conf import settings


def schedule_function(queue_name, function_name, *args, **kwargs):
    """
    Schedule a function named `function_name` to be run by workers on
    the queue `queue_name` with *args and **kwargs as specified by that
    function.
    """
    body = create_request_body(function_name, *args, **kwargs)
    connection = boto.connect_sqs(
        settings.BEANSTALK_DISPATCH_SQS_KEY,
        settings.BEANSTALK_DISPATCH_SQS_SECRET)
    queue = connection.get_queue(queue_name)
    if not queue:
        queue = connection.create_queue(queue_name)
    message = boto.sqs.message.Message()
    message.set_body(body)
    queue.write(message)
