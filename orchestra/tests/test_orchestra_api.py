import json
from unittest.mock import patch
from unittest.mock import PropertyMock

from django.test import TestCase
from rest_framework.test import APIClient

from orchestra.tests.helpers.fixtures import TodoFactory
from orchestra.tests.helpers.fixtures import StepFactory
from orchestra.tests.helpers.fixtures import ProjectFactory
from orchestra.project_api.auth import SignedUser
from orchestra.orchestra_api import get_project_information
from orchestra.orchestra_api import create_todos
from orchestra.orchestra_api import get_todos


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

    @patch('orchestra.orchestra_api.requests')
    def test_(self, mock_request):
        def get(url, *args, **kwargs):
            return_value = self.request_client.get(url, format='json')
            return_value.text = json.dumps(return_value.data)
            return return_value

        mock_request.get = get

        step_1 = StepFactory(slug='step_1')
        step_2 = StepFactory(slug='step_2')
        project2 = ProjectFactory()
        # 2 todos have the same project
        todo1 = TodoFactory(step=step_1, project=self.project)
        todo2 = TodoFactory(step=step_1, project=self.project)
        # 1 todo has another project
        todo3 = TodoFactory(step=step_2, project=project2)

        todo4 = TodoFactory(step=step_1, project=project2)

        # Get todo1 and todo2
        res = get_todos(self.project.id, step_1.slug)
        self.assertEqual(len(res), 2)
        expected_ids = [todo1.id, todo2.id]
        for r in res:
            self.assertIn(r['id'], expected_ids)

        # Get todo3
        res = get_todos(project2.id, step_2.slug)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['id'], todo3.id)

        # Filter by step slug
        res = get_todos(project_id=None, step_slug=step_1.slug)
        self.assertEqual(len(res), 3)
        expected_ids = [todo1.id, todo2.id, todo4.id]
        for r in res:
            self.assertIn(r['id'], expected_ids)

        # Filter by project_id
        res = get_todos(project_id=project2.id)
        self.assertEqual(len(res), 2)
        expected_ids = [todo3.id, todo4.id]
        for r in res:
            self.assertIn(r['id'], expected_ids)

        # Get all todos
        res = get_todos()
        self.assertEqual(len(res), 4)
        expected_ids = [todo1.id, todo2.id, todo3.id, todo4.id]
        for r in res:
            self.assertIn(r['id'], expected_ids)
