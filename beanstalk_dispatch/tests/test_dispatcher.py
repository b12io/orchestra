import json

from base64 import b64encode
from beanstalk_dispatch import ARGS
from beanstalk_dispatch import FUNCTION
from beanstalk_dispatch import KWARGS
from beanstalk_dispatch.common import create_request_body
from django.core.urlresolvers import reverse
from django.test import Client
from django.test import TestCase
from django.test import override_settings

CALL_COUNTER = 0


def counter_incrementer(first_arg, second_arg=None):
    global CALL_COUNTER
    CALL_COUNTER += first_arg
    if second_arg:
        CALL_COUNTER += second_arg


DISPATCH_SETTINGS = {
    'BEANSTALK_DISPATCH_TABLE': {
        'the_counter': ('beanstalk_dispatch.tests.'
                        'test_dispatcher.counter_incrementer')
    }
}


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

    @override_settings(**DISPATCH_SETTINGS)
    def test_no_get(self):
        response = self.client.get(self.url)
        self.assertEquals(response.status_code, 405)

    @override_settings(BEANSTALK_DISPATCH_TABLE=None)
    def test_no_dispatch(self):
        response = self.client.post(
            self.url, b64encode(
                create_request_body('some_func').encode('ascii')),
            content_type='application/json')
        self.assertEquals(response.status_code, 400)
        self.assertEquals(json.loads(response.content.decode()),
                          {'message': 'No beanstalk dispatch table configured',
                           'error': 400})

    @override_settings(**DISPATCH_SETTINGS)
    def test_missing_function(self):
        response = self.client.post(
            self.url,
            b64encode(create_request_body('nonexistent_func').encode('ascii')),
            content_type='application/json')
        self.assertEquals(response.status_code, 400)
        self.assertEquals(
            json.loads(response.content.decode()),
            {'message': 'Requested function not found: nonexistent_func',
                'error': 400})

    @override_settings(**DISPATCH_SETTINGS)
    def test_malformed_request(self):
        keys = {FUNCTION, ARGS, KWARGS}
        for missing_key in keys:
            request_body = {key: 'test' for key in
                            keys - {missing_key}}
            response = self.client.post(
                self.url,
                b64encode(json.dumps(request_body).encode('ascii')),
                content_type='application/json')
            self.assertEquals(response.status_code, 400)
            self.assertEquals(json.loads(response.content.decode()), {
                'message': 'Please provide a {} argument'.format(missing_key),
                'error': 400})

    @override_settings(**DISPATCH_SETTINGS)
    def test_both_args_kwargs(self):
        body = b64encode(
            create_request_body('the_counter', 1, second_arg=5)
            .encode('ascii'))
        response = self.client.post(self.url,
                                    body,
                                    content_type='application/json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(json.loads(response.content.decode()),
                          {})
        self.assertEquals(CALL_COUNTER, 6)

    @override_settings(**DISPATCH_SETTINGS)
    def test_just_args(self):
        body = b64encode(create_request_body('the_counter', 2).encode('ascii'))
        response = self.client.post(self.url,
                                    body,
                                    content_type='application/json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(json.loads(response.content.decode()),
                          {})
        self.assertEquals(CALL_COUNTER, 2)
