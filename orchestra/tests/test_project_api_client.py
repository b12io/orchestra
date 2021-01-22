import json
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from orchestra.models import Todo
from orchestra.tests.helpers.fixtures import TodoFactory
from orchestra.tests.helpers.fixtures import TodoListTemplateFactory
from orchestra.tests.helpers.fixtures import StepFactory
from orchestra.tests.helpers.fixtures import ProjectFactory
from orchestra.tests.helpers.fixtures import WorkflowVersionFactory
from orchestra.project_api.auth import SignedUser
from orchestra.orchestra_api import create_todos
from orchestra.orchestra_api import get_todos
from orchestra.orchestra_api import get_todo_templates
from orchestra.orchestra_api import create_todos_from_template
from orchestra.orchestra_api import update_todos
from orchestra.orchestra_api import delete_todos
from orchestra.orchestra_api import OrchestraError


class TodoTemplatesAPITests(TestCase):
    def setUp(self):
        super().setUp()
        self.request_client = APIClient(enforce_csrf_checks=True)
        self.request_client.force_authenticate(user=SignedUser())

        self.todolist_template_slug = 'test_todolist_template_slug'
        self.todolist_template_name = 'test_todolist_template_name'
        self.todolist_template_description = \
            'test_todolist_template_description'
        self.workflow_version = WorkflowVersionFactory()
        self.step = StepFactory(
            slug='step-slug',
            workflow_version=self.workflow_version)
        self.project = ProjectFactory(
            workflow_version=self.workflow_version)

    @patch('orchestra.orchestra_api.requests')
    def test_get_todo_templates(self, mock_request):
        # This converts `requests.get` into DRF's `APIClient.get`
        # To make it testable
        def get(url, *args, **kwargs):
            return_value = self.request_client.get(url, format='json')
            return_value.text = json.dumps(return_value.data)
            return return_value

        mock_request.get = get

        template1 = TodoListTemplateFactory()
        template2 = TodoListTemplateFactory()

        # Get template1 and template2
        res = get_todo_templates()
        self.assertEqual(len(res), 2)
        expected_ids = [template1.id, template2.id]
        for r in res:
            self.assertIn(r['id'], expected_ids)

        # # Get newly created template3
        template3 = TodoListTemplateFactory()
        res = get_todo_templates()
        self.assertEqual(len(res), 3)
        self.assertEqual(res[2]['id'], template3.id)

    @patch('orchestra.orchestra_api.requests')
    def test_create_todos_from_template(self, mock_request):
        # This converts `requests.post` into DRF's `APIClient.post`
        # To make it testable
        def post(url, *args, **kwargs):
            kw = kwargs.get('data', '')
            data = json.loads(kw)
            return_value = self.request_client.post(url, data, format='json')
            return_value.text = json.dumps(return_value.json())
            return return_value

        todolist_template = TodoListTemplateFactory(
            slug=self.todolist_template_slug,
            name=self.todolist_template_name,
            description=self.todolist_template_description,
            todos={'items': [{
                'id': 1,
                'description': 'todo parent',
                'project': self.project.id,
                'step': self.step.slug,
                'items': [{
                    'id': 2,
                    'project': self.project.id,
                    'step': self.step.slug,
                    'description': 'todo child',
                    'items': []
                }]
            }]},
        )

        mock_request.post = post
        additional_data = {
            'some_additional_data': 'value'
        }
        result = create_todos_from_template(
            self.todolist_template_slug,
            self.project.id,
            self.step.slug,
            additional_data)
        self.assertEqual(result['success'], True)
        self.assertEqual(len(result['todos']), 3)
        for t in result['todos']:
            self.assertEqual(t['template'], todolist_template.id)
            self.assertEqual(t['section'], None)
            self.assertEqual(t['additional_data'], additional_data)

    @patch('orchestra.orchestra_api.requests')
    def test_create_todos_from_template_key_error(self, mock_request):
        # This converts `requests.post` into DRF's `APIClient.post`
        # To make it testable
        def post(url, *args, **kwargs):
            kw = kwargs.get('data', '')
            data = json.loads(kw)
            return_value = self.request_client.post(url, data, format='json')
            return_value.text = json.dumps(return_value.json())
            return return_value

        TodoListTemplateFactory(
            slug=self.todolist_template_slug,
            name=self.todolist_template_name,
            description=self.todolist_template_description,
            todos={'items': [{
                'id': 1,
                'description': 'todo parent',
                'project': self.project.id,
                'step': self.step.slug,
                'items': [{
                    'id': 2,
                    'project': self.project.id,
                    'step': self.step.slug,
                    'description': 'todo child',
                    'items': []
                }]
            }]},
        )

        mock_request.post = post
        additional_data = {
            'some_additional_data': 'value'
        }
        result = create_todos_from_template(
            self.todolist_template_slug,
            self.project.id,
            None,
            additional_data)
        err_msg = ('An object with `template_slug`, `step_slug`,'
                   ' and `project_id` attributes should be supplied')
        self.assertEqual(result['success'], False)
        self.assertEqual(len(result['errors']), 1)
        self.assertEqual(result['errors']['error'], err_msg)

    @patch('orchestra.orchestra_api.requests')
    def test_create_todos_from_template_unknown_step_slug(self, mock_request):
        # This converts `requests.post` into DRF's `APIClient.post`
        # To make it testable
        def post(url, *args, **kwargs):
            kw = kwargs.get('data', '')
            data = json.loads(kw)
            return_value = self.request_client.post(url, data, format='json')
            return_value.text = json.dumps(return_value.json())
            return return_value

        TodoListTemplateFactory(
            slug=self.todolist_template_slug,
            name=self.todolist_template_name,
            description=self.todolist_template_description,
            todos={'items': [{
                'id': 1,
                'description': 'todo parent',
                'project': self.project.id,
                'step': self.step.slug,
                'items': [{
                    'id': 2,
                    'project': self.project.id,
                    'step': self.step.slug,
                    'description': 'todo child',
                    'items': []
                }]
            }]},
        )

        mock_request.post = post
        additional_data = {
            'some_additional_data': 'value'
        }
        result = create_todos_from_template(
            self.todolist_template_slug,
            self.project.id,
            'unknown-step-slug',
            additional_data)
        self.assertEqual(result['success'], False)
        self.assertEqual(len(result['errors']), 1)


class TodoAPITests(TestCase):
    def setUp(self):
        super().setUp()
        self.request_client = APIClient(enforce_csrf_checks=True)
        self.request_client.force_authenticate(user=SignedUser())
        self.workflow_version = WorkflowVersionFactory()
        self.step = StepFactory(
            slug='step-slug',
            workflow_version=self.workflow_version)
        self.project = ProjectFactory(
            workflow_version=self.workflow_version)

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
                'step': self.step.slug
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
        # This converts `requests.patch` into DRF's `APIClient.patch`
        # To make it testable
        def patch_func(url, *args, **kwargs):
            kw = kwargs.get('data', '')
            data = json.loads(kw)
            return_value = self.request_client.put(
                url, data, format='json')
            return_value.text = json.dumps(return_value.data)
            return return_value

        mock_request.patch = patch_func

        todo1 = TodoFactory(step=self.step, project=self.project)
        todo2 = TodoFactory(step=self.step, project=self.project)
        todo3 = TodoFactory(step=self.step, project=self.project)
        todo_should_not_be_updated = TodoFactory(
            project=self.project, step=self.step, title='Not updated')
        # Change titles
        todos_with_updated_titles = [{
            'id': x.id,
            'title': 'Updated title {}'.format(x.id),
            'step': x.step.slug,
            'project': x.project.id
        } for x in [todo1, todo3, todo2]]
        result = update_todos(todos_with_updated_titles)
        self.assertEqual(len(result), 3)
        updated_todos = Todo.objects.filter(
            id__in=[todo1.id, todo2.id, todo3.id])
        for todo in updated_todos:
            self.assertEqual(todo.title, 'Updated title {}'.format(todo.id))
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
