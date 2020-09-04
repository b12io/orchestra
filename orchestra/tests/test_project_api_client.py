import json
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from orchestra.models import Todo
from orchestra.todos.serializers import BulkTodoSerializer
from orchestra.tests.helpers.fixtures import TodoFactory
from orchestra.tests.helpers.fixtures import StepFactory
from orchestra.tests.helpers.fixtures import ProjectFactory
from orchestra.project_api.auth import SignedUser
from orchestra.orchestra_api import create_todos
from orchestra.orchestra_api import get_todos
from orchestra.orchestra_api import update_todos
from orchestra.orchestra_api import delete_todos
from orchestra.orchestra_api import OrchestraError


class TodoAPITests(TestCase):
    def setUp(self):
        super().setUp()
        self.request_client = APIClient(enforce_csrf_checks=True)
        self.request_client.force_authenticate(user=SignedUser())
        self.project = ProjectFactory()
        self.step = StepFactory()

    @patch('orchestra.orchestra_api.requests')
    def test_create_todos(self, mock_request):
        # This converts `requests.post` into DRF's `APIClient.post`
        # To make it testable
        def post(url, *args, **kwargs):
            kw = kwargs.get('data', '')
            data = json.loads(kw)
            return_value = self.request_client.post(url, data, format='json')
            return_value.text = json.dumps(return_value.data)
            return return_value

        mock_request.post = post
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
    def test_get_todos(self, mock_request):
        # This converts `requests.get` into DRF's `APIClient.get`
        # To make it testable
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

        # Filter by project_id
        res = get_todos(project_id=project2.id)
        self.assertEqual(len(res), 2)
        expected_ids = [todo3.id, todo4.id]
        for r in res:
            self.assertIn(r['id'], expected_ids)

        # Test project_id is required
        msg = 'project_id is required'
        with self.assertRaisesMessage(OrchestraError, msg):
            get_todos(None)

    @patch('orchestra.orchestra_api.requests')
    def test_update_todos(self, mock_request):
        # This converts `requests.put` into DRF's `APIClient.put`
        # To make it testable
        def put(url, *args, **kwargs):
            kw = kwargs.get('data', '')
            data = json.loads(kw)
            return_value = self.request_client.put(
                url, data, format='json')
            return_value.text = json.dumps(return_value.data)
            return return_value

        mock_request.put = put

        todo1 = TodoFactory(step=self.step, project=self.project)
        todo2 = TodoFactory(step=self.step, project=self.project)
        todo3 = TodoFactory(step=self.step, project=self.project)
        todo_should_not_be_updated = TodoFactory(
            project=self.project, step=self.step, title='Not updated')
        serialized = BulkTodoSerializer([todo1, todo2, todo3], many=True).data
        # Change titles
        updated = [
            self._change_attr(x, 'title',  'updated title {}'.format(x['id']))
            for x in serialized]
        result = update_todos(updated)
        self.assertEqual(len(result), 3)
        updated_todos = Todo.objects.filter(
            id__in=[todo1.id, todo2.id, todo3.id])
        for todo in updated_todos:
            self.assertTrue(todo.title.startswith('updated title'))
        self.assertEqual(todo_should_not_be_updated.title, 'Not updated')

    def _change_attr(self, item, attr, value):
        item[attr] = value
        return item

    @patch('orchestra.orchestra_api.requests')
    def test_delete_todos(self, mock_request):
        # This converts `requests.delete` into DRF's `APIClient.delete`
        # To make it testable
        def delete(url, *args, **kwargs):
            kw = kwargs.get('data', '')
            data = json.loads(kw)
            return_value = self.request_client.delete(
                url, data, format='json')
            return_value.text = json.dumps(return_value.data)
            return return_value

        mock_request.delete = delete

        todo1 = TodoFactory(step=self.step, project=self.project)
        todo2 = TodoFactory(step=self.step, project=self.project)
        todo3 = TodoFactory(step=self.step, project=self.project)
        todo4 = TodoFactory(step=self.step, project=self.project)

        res = delete_todos([todo1.id, todo2.id, todo3.id])
        self.assertEqual(res[0], 3)
        left_todos = Todo.objects.all()
        self.assertEqual(left_todos.count(), 1)
        self.assertEqual(left_todos[0].id, todo4.id)
