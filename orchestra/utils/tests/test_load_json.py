import json

from orchestra.tests.helpers import OrchestraTestCase
from orchestra.utils.load_json import load_encoded_json


class LoadEncodedJsonTest(OrchestraTestCase):

    def test_non_json_string(self):
        encoded_data = ''
        result = load_encoded_json(encoded_data)
        expected = {}
        self.assertEqual(result, expected)

    def test_decode_error(self):
        encoded_data = 1
        result = load_encoded_json(encoded_data)
        expected = {}
        self.assertEqual(result, expected)

    def test_valid(self):
        expected = {'test_key': 'test_value'}
        encoded_data = json.dumps(expected).encode()
        result = load_encoded_json(encoded_data)
        self.assertEqual(result, expected)
