import boto
import json

from beanstalk_dispatch import ARGS
from beanstalk_dispatch import FUNCTION
from beanstalk_dispatch import KWARGS
from beanstalk_dispatch.client import schedule_function
from django.test import TestCase
from django.test import override_settings
from moto import mock_sqs

CALL_COUNTER = 0


def counter_incrementer(first_arg, second_arg=None):
    global CALL_COUNTER
    CALL_COUNTER += first_arg
    if second_arg:
        CALL_COUNTER += second_arg


DISPATCH_SETTINGS = {
    'BEANSTALK_DISPATCH_TABLE': {
        'the_counter': ('beanstalk_dispatch.tests.'
                        'test_client.counter_incrementer')
    }
}


@mock_sqs
@override_settings(
    BEANSTALK_DISPATCH_SQS_KEY='', BEANSTALK_DISPATCH_SQS_SECRET='')
class ClientTestCase(TestCase):

    def setUp(self):
        self.queue_name = 'testing-queue'

    def test_async_function_scheduling(self):
        # Check the message on the queue.
        sqs_connection = boto.connect_sqs('', '')
        sqs_connection.create_queue(self.queue_name)
        queue = sqs_connection.get_queue(self.queue_name)
        messages = queue.get_messages()
        self.assertEquals(len(messages), 0)

        # Schedule a function.
        schedule_function(
            self.queue_name, 'a-function', '1', '2', kwarg1=1, kwarg2=2)

        messages = queue.get_messages()
        self.assertEquals(len(messages), 1)

        # For some reason, boto base64-encodes the messages, but moto does
        # not.  Life.
        self.assertEquals(
            json.loads(messages[0].get_body()),
            {FUNCTION: 'a-function', ARGS: ['1', '2'], KWARGS: {
                'kwarg1': 1, 'kwarg2': 2}})

    @override_settings(
        BEANSTALK_DISPATCH_EXECUTE_SYNCHRONOUSLY=True,
        **DISPATCH_SETTINGS
    )
    def test_sync_function_scheduling(self):
        # Schedule a function.
        schedule_function(self.queue_name, 'the_counter', 1, second_arg=5)

        self.assertEquals(CALL_COUNTER, 6)
