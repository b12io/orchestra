import json

from base64 import b64encode
from beanstalk_dispatch import ARGS
from beanstalk_dispatch import FUNCTION
from beanstalk_dispatch import KWARGS
from beanstalk_dispatch.common import create_request_body
from beanstalk_dispatch.safe_task import SafeTask
from django.core.urlresolvers import reverse
from django.test import Client
from django.test import TestCase
from django.test import override_settings

from orchestra.utils.load_json import load_encoded_json

CALL_COUNTER = 0


def counter_incrementer(first_arg, second_arg=None):
    global CALL_COUNTER
    CALL_COUNTER += first_arg
    if second_arg:
        CALL_COUNTER += second_arg


class CounterIncrementerTask(SafeTask):

    def run(self, *args, **kwargs):
        counter_incrementer(*args, **kwargs)


class BadTaskClass(object):
    pass


DISPATCH_SETTINGS = {
    'BEANSTALK_DISPATCH_TABLE': {
        'the_counter': ('beanstalk_dispatch.tests.'
                        'test_dispatcher.counter_incrementer'),
        'the_counter_task': ('beanstalk_dispatch.tests.'
                             'test_dispatcher.CounterIncrementerTask'),
        'bad_task_class': ('beanstalk_dispatch.tests.'
                           'test_dispatcher.BadTaskClass'),
        'bad_function_pointer': 'nothing-to-see-here',
    }
}


@override_settings(**DISPATCH_SETTINGS)
class DispatcherTestCase(TestCase):

    """ Test the server-side function dispatcher.

    In these tests, we base64-encode every message we send to the server
    because this is what boto does.
    """

    def setUp(self):
        global CALL_COUNTER
        CALL_COUNTER = 0
        self.client = Client()
        self.url = reverse('beanstalk_dispatcher')

    def test_no_get(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    @override_settings(BEANSTALK_DISPATCH_TABLE=None)
    def test_no_dispatch(self):
        response = self.client.post(
            self.url, b64encode(
                create_request_body('some_func').encode('ascii')),
            content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(load_encoded_json(response.content),
                         {'message': 'No beanstalk dispatch table configured',
                          'error': 400})

    def test_missing_function(self):
        response = self.client.post(
            self.url,
            b64encode(create_request_body('nonexistent_func').encode('ascii')),
            content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            load_encoded_json(response.content),
            {
                'message': 'Requested function not found: nonexistent_func',
                'error': 400
            })

    def test_invalid_task_class(self):
        response = self.client.post(
            self.url,
            b64encode(create_request_body(
                'bad_task_class', 'test-queue', {}).encode('ascii')),
            content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            load_encoded_json(response.content),
            {
                'message': ('Requested task is not a SafeTask'
                            ' subclass: bad_task_class'),
                'error': 400
            })

    def test_invalid_function_pointer(self):
        response = self.client.post(
            self.url,
            b64encode(create_request_body(
                'bad_function_pointer', 'test-queue', {}).encode('ascii')),
            content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            load_encoded_json(response.content),
            {
                'message': 'Unable to locate function: nothing-to-see-here',
                'error': 400
            })

    def test_malformed_request(self):
        keys = {FUNCTION, ARGS, KWARGS}
        for missing_key in keys:
            request_body = {key: 'test' for key in
                            keys - {missing_key}}
            response = self.client.post(
                self.url,
                b64encode(json.dumps(request_body).encode('ascii')),
                content_type='application/json')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(load_encoded_json(response.content), {
                'message': 'Please provide a {} argument'.format(missing_key),
                'error': 400})

    def test_both_args_kwargs(self):
        body = b64encode(
            create_request_body('the_counter', 1, second_arg=5)
            .encode('ascii'))
        response = self.client.post(self.url,
                                    body,
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(load_encoded_json(response.content), {})
        self.assertEqual(CALL_COUNTER, 6)

    def test_just_args(self):
        body = b64encode(create_request_body('the_counter', 2).encode('ascii'))
        response = self.client.post(self.url,
                                    body,
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(load_encoded_json(response.content), {})
        self.assertEqual(CALL_COUNTER, 2)

    def test_just_args_task(self):
        body = b64encode(create_request_body(
            'the_counter_task', 2).encode('ascii'))
        response = self.client.post(self.url,
                                    body,
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(load_encoded_json(response.content), {})
        self.assertEqual(CALL_COUNTER, 2)

    def test_both_args_kwargs_task(self):
        body = b64encode(
            create_request_body('the_counter_task', 1, second_arg=5)
            .encode('ascii'))
        response = self.client.post(self.url,
                                    body,
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(load_encoded_json(response.content), {})
        self.assertEqual(CALL_COUNTER, 6)
