import json
from unittest.mock import patch
from unittest.mock import PropertyMock

from django.test import TestCase
from rest_framework.test import APIClient

from orchestra.tests.helpers.fixtures import StepFactory
from orchestra.tests.helpers.fixtures import ProjectFactory
from orchestra.orchestra_api import create_todos
from orchestra.orchestra_api import get_project_information
from orchestra.project_api.auth import SignedUser


class TodoAPITests(TestCase):
    def setUp(self):
        super().setUp()
        self.request_client = APIClient(enforce_csrf_checks=True)
        self.request_client.force_authenticate(user=SignedUser())
        self.project = ProjectFactory()
        self.step = StepFactory()
    
    def _pause(self):
        self.assertTrue(False)

    @patch('orchestra.orchestra_api.requests')
    def test_create_todos(self, mock_request_post):
        # This converts DRF's `APIClient.post` into `requests.post`
        def post(url, *args, **kwargs):
            kw = kwargs.get('data', '')
            data = json.loads(kw)
            return_value = self.request_client.post(url, data, format='json')
            return_value.text = json.dumps(return_value.data)
            return return_value

        mock_request_post.post = post
        data = [
            {
                'title': 'Testing title {}'.format(x),
                'project': self.project.id,
                'step': self.step.id
            } for x in range(10)
        ]
        result = create_todos(data)
        self.assertEqual(len(result), 10)
        for r in result:
            self.assertTrue(r['title'].startswith('Testing title'))
