import copy
import csv
import json

from django.utils import timezone
from dateutil.parser import parse
from django.urls import reverse
from io import StringIO
from unittest.mock import patch

from orchestra.models import Task
from orchestra.models import Todo
from orchestra.models import TodoQA
from orchestra.models import TodoListTemplate
from orchestra.models import TodoListTemplateImportRecord
from orchestra.models import Worker
from orchestra.project_api.serializers import TimeEntrySerializer
from orchestra.tests.helpers import EndpointTestCase
from orchestra.tests.helpers import OrchestraTransactionTestCase
from orchestra.tests.helpers.fixtures import TaskFactory
from orchestra.tests.helpers.fixtures import TodoFactory
from orchestra.tests.helpers.fixtures import StepFactory
from orchestra.tests.helpers.fixtures import ProjectFactory
from orchestra.tests.helpers.fixtures import TodoQAFactory
from orchestra.tests.helpers.fixtures import WorkflowVersionFactory
from orchestra.tests.helpers.fixtures import TodoListTemplateFactory
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.tests.helpers.fixtures import TODO_TEMPLATE_BAD_HEADER_CSV_TEXT
from orchestra.tests.helpers.fixtures import TODO_TEMPLATE_GOOD_CSV_TEXT
from orchestra.tests.helpers.fixtures import (
    TODO_TEMPLATE_INVALID_PARENT_CSV_TEXT)
from orchestra.tests.helpers.fixtures import TODO_TEMPLATE_NESTED_TODOS
from orchestra.tests.helpers.fixtures import TODO_TEMPLATE_TWO_ENTRIES_CSV_TEXT
from orchestra.todos.serializers import TodoQASerializer
from orchestra.todos.serializers import BulkTodoSerializerWithoutQA
from orchestra.todos.serializers import TodoListTemplateSerializer
from orchestra.utils.load_json import load_encoded_json


def _todo_data(title, completed,
               skipped_datetime=None, start_by=None,
               due=None, parent_todo=None, template=None,
               activity_log=str({'actions': []}), qa=None,
               project=None, step=None, details=None, is_deleted=False):
    if skipped_datetime:
        status = Todo.Status.DECLINED.value
    elif completed:
        status = Todo.Status.COMPLETED.value
    else:
        status = Todo.Status.PENDING.value
    return {
        'completed': completed,
        'title': title,
        'template': template,
        'parent_todo': parent_todo,
        'start_by_datetime': start_by,
        'due_datetime': due,
        'activity_log': activity_log,
        'skipped_datetime': skipped_datetime,
        'qa': qa,
        'additional_data': {},
        'order': None,
        'project': project,
        'section': None,
        'status': status,
        'step': step,
        'details': details,
        'is_deleted': is_deleted
    }


def _get_test_conditional_props(project):
    return {
        'prop1': True,
        'prop2': False
    }


class TodosEndpointTests(EndpointTestCase):

    def setUp(self):
        super().setUp()
        setup_models(self)
        self.worker = Worker.objects.get(user__username='test_user_6')
        self.request_client.login(username=self.worker.user.username,
                                  password='defaultpassword')
        self.list_create_url = reverse('orchestra:todos:todos-list')
        self.list_details_url_name = 'orchestra:todos:todos-detail'
        self.workflow_version = WorkflowVersionFactory()
        self.step = StepFactory(
            slug='step-slug',
            workflow_version=self.workflow_version)
        self.project = ProjectFactory(
            workflow_version=self.workflow_version)
        tasks = Task.objects.filter(assignments__worker=self.worker)
        task = tasks[0]
        task.project = self.project
        task.step = self.step
        task.save()
        self.todo_title = 'Let us do this'
        self.deadline = parse('2018-01-16T07:03:00+00:00')

    def _verify_missing_task(self, response):
        self.assertEqual(response.status_code, 400)
        data = load_encoded_json(response.content)
        self.assertEqual(data['message'], 'No task for given id')
        self.assertEqual(data['error'], 400)

    def _verify_worker_not_assigned(self, response):
        self.assertEqual(response.status_code, 400)
        data = load_encoded_json(response.content)
        self.assertEqual(data['message'],
                         'Worker is not assigned to this task id.')
        self.assertEqual(data['error'], 400)

    def _verify_time_entries(self, data):
        for time_entry in data:
            serializer = TimeEntrySerializer(data=time_entry)
            self.assertTrue(serializer.is_valid())

    def _verify_todo_content(self, todo, expected_todo):
        todo = dict(todo)
        created_at = todo.pop('created_at')
        todo_id = todo.pop('id')
        self.assertEqual(todo, expected_todo)
        self.assertGreater(len(created_at), 0)
        self.assertGreaterEqual(todo_id, 0)

    def _verify_todos_list(self, project_id, expected_todos, success):
        resp = self.request_client.get(self.list_create_url,
                                       {'project__id': project_id})
        if success:
            self.assertEqual(resp.status_code, 200)
            data = load_encoded_json(resp.content)
            for todo, expected_todo in zip(data, expected_todos):
                self._verify_todo_content(todo, expected_todo)
        else:
            self.assertEqual(resp.status_code, 403)

    @patch('orchestra.todos.views.notify_todo_created')
    def _verify_todo_creation(self, success, project, step, mock_notify):
        num_todos = Todo.objects.all().count()
        resp = self.request_client.post(self.list_create_url, {
            'project': project,
            'step': step.slug,
            'title': self.todo_title,
            'status': Todo.Status.PENDING.value})
        if success:
            self.assertEqual(resp.status_code, 201)
            self.assertEqual(Todo.objects.all().count(), num_todos + 1)
            todo = load_encoded_json(resp.content)
            self._verify_todo_content(
                todo, _todo_data(
                    self.todo_title, False, project=project, step=step.slug))
            self.assertTrue(mock_notify.called)
        else:
            self.assertEqual(resp.status_code, 403)
            self.assertEqual(Todo.objects.all().count(), num_todos)

    @patch('orchestra.todos.views.notify_single_todo_update')
    def _verify_todo_update(self, todo, success, mock_notify):
        title = 'new title'
        list_details_url = reverse(
            self.list_details_url_name,
            kwargs={'pk': todo.id})
        resp = self.request_client.put(
            list_details_url,
            json.dumps(_todo_data(
                title, True,
                project=self.project.id, step=self.step.slug)),
            content_type='application/json')
        updated_todo = BulkTodoSerializerWithoutQA(
            Todo.objects.get(id=todo.id)).data
        if success:
            self.assertEqual(resp.status_code, 200)
            self._verify_todo_content(
                updated_todo, _todo_data(
                    title, True,
                    project=self.project.id,
                    step=self.step.slug))
            self.assertTrue(mock_notify.called)
        else:
            self.assertEqual(resp.status_code, 403)
            self.assertNotEqual(updated_todo['title'], title)

    def test_todos_list_create(self):
        self._verify_todos_list(self.project.id, [], True)
        self._verify_todo_creation(
            True, self.project.id, self.step)
        self._verify_todos_list(self.project.id,
                                [_todo_data(
                                    self.todo_title,
                                    False,
                                    project=self.project.id,
                                    step=self.step.slug)],
                                True)

    def test_todos_list_create_permissions(self):
        # Can't make requests for projects in which you're uninvolved.
        project = ProjectFactory()
        step = StepFactory()
        self._verify_todos_list(project.id, [], False)
        self._verify_todo_creation(False, project.id, step)

    def test_todo_details_and_permissions(self):
        # You should be able to update Todos for projects in which
        # you're involved, and not for other projects.
        good_todo = TodoFactory(project=self.project, step=self.step)
        self._verify_todo_update(good_todo, True)
        bad_todo = TodoFactory()
        self._verify_todo_update(bad_todo, False)

    def test_create_todo_with_start_by_datetime(self):
        START_TITLE = 'Start soon'

        start_by_todo = TodoFactory(
            project=self.project,
            step=self.step,
            start_by_datetime=self.deadline,
            title=START_TITLE,
            status=Todo.Status.PENDING.value)

        self._verify_todos_list(start_by_todo.project.id, [
            _todo_data(
                START_TITLE,
                False,
                None,
                self.deadline.strftime('%Y-%m-%dT%H:%M:%SZ'),
                None,
                project=start_by_todo.project.id,
                step=start_by_todo.step.slug)
        ], True)

    def test_create_todo_with_due_datetime(self):
        DUE_TITLE = 'Due soon'

        due_todo = TodoFactory(
            project=self.project,
            step=self.step,
            due_datetime=self.deadline,
            title=DUE_TITLE,
            status=Todo.Status.PENDING.value)

        self._verify_todos_list(due_todo.project.id, [
            _todo_data(
                DUE_TITLE,
                False,
                None,
                None,
                self.deadline.strftime('%Y-%m-%dT%H:%M:%SZ'),
                project=due_todo.project.id,
                step=due_todo.step.slug),
        ], True)

    def test_todo_deletion(self):
        todo = TodoFactory(project=self.project, step=self.step)
        deletion_url = reverse(
            self.list_details_url_name,
            kwargs={'pk': todo.id})
        resp = self.request_client.delete(deletion_url)
        self.assertEqual(resp.status_code, 204)


class TodoQAEndpointTests(EndpointTestCase):

    def setUp(self):
        super().setUp()
        setup_models(self)
        self.worker = Worker.objects.get(user__username='test_user_6')
        self.request_client.login(username=self.worker.user.username,
                                  password='defaultpassword')
        self.list_create_url = reverse('orchestra:todos:todo_qas')
        self.worker_task_recent_todo_qas_url = reverse(
            'orchestra:todos:worker_task_recent_todo_qas')
        self.list_details_url_name = 'orchestra:todos:todo_qa'
        self.project0 = ProjectFactory()
        self.project1 = ProjectFactory()
        self.step = StepFactory(slug='some-slug')
        tasks = Task.objects.filter(
            assignments__worker=self.worker)
        self.task_0 = tasks[0]
        self.task_0.project = self.project0
        self.task_0.step = self.step
        self.task_0.save()
        self.task_1 = tasks[1]
        self.task_1.project = self.project1
        self.task_1.step = self.step
        self.task_1.save()
        self.todo = TodoFactory(project=self.project0, step=self.step)
        self.comment = 'Test comment'

    def _todo_qa_data(
            self, todo, approved, comment):
        return {
            'todo': todo.id,
            'approved': approved,
            'comment': comment
        }

    def _verify_todo_qa_content(self, todo_qa,
                                expected_todo_qa):
        todo_qa = dict(todo_qa)
        created_at = todo_qa.pop('created_at')
        todo_qa_id = todo_qa.pop('id')
        self.assertEqual(todo_qa, expected_todo_qa)
        self.assertGreater(len(created_at), 0)
        self.assertGreaterEqual(todo_qa_id, 0)

    def _verify_todo_qa_creation(self, todo, success):
        num_todo_qas = TodoQA.objects.all().count()
        resp = self.request_client.post(self.list_create_url, {
            'todo': todo.id,
            'approved': True,
            'comment': self.comment})
        if success:
            self.assertEqual(resp.status_code, 201)
            self.assertEqual(TodoQA.objects.all().count(), num_todo_qas + 1)
            todo_qa = load_encoded_json(resp.content)
            self._verify_todo_qa_content(todo_qa, self._todo_qa_data(
                todo, True, self.comment))
        else:
            self.assertEqual(resp.status_code, 403)
            self.assertEqual(TodoQA.objects.all().count(), num_todo_qas)

    def _verify_todo_qa_update(self, todo_qa, success):
        comment = 'new comment'
        list_details_url = reverse(
            self.list_details_url_name,
            kwargs={'pk': todo_qa.id})
        resp = self.request_client.put(
            list_details_url,
            json.dumps(self._todo_qa_data(
                todo_qa.todo, True, comment)),
            content_type='application/json')
        updated_todo_qa = TodoQASerializer(
            TodoQA.objects.get(id=todo_qa.id)).data
        if success:
            self.assertEqual(resp.status_code, 200)
            self._verify_todo_qa_content(updated_todo_qa, self._todo_qa_data(
                todo_qa.todo, True, comment))
        else:
            self.assertEqual(resp.status_code, 403)
            self.assertNotEqual(
                updated_todo_qa['comment'], comment)

    def test_todo_qas_list_create(self):
        self._verify_todo_qa_creation(self.todo, True)

    def test_todo_qas_create_permissions(self):
        # Can't make requests for projects in which you're uninvolved.
        project = ProjectFactory()
        step = StepFactory()
        todo = TodoFactory(project=project, step=step)
        self._verify_todo_qa_creation(todo, False)

    def test_todo_qa_details_and_permissions(self):
        # You should be able to update TodoQAs for projects in which
        # you're involved, and not for other projects.
        good_todo_qa = TodoQAFactory(todo=self.todo)
        self._verify_todo_qa_update(good_todo_qa, True)
        bad_todo_qa = TodoQAFactory()
        self._verify_todo_qa_update(bad_todo_qa, False)

    def _verify_worker_task_recent_todo_qas(self, task, todo_qa, success):
        resp = self.request_client.get(self.worker_task_recent_todo_qas_url,
                                       {'task': task.id})
        if success:
            self.assertEqual(resp.status_code, 200)
            data = load_encoded_json(resp.content)
            if todo_qa:
                self.assertEqual(
                    TodoQASerializer(todo_qa).data,
                    list(data.values())[0])
                self.assertEqual(1, len(data.keys()))
            else:
                self.assertEqual({}, data)
        else:
            self.assertEqual(resp.status_code, 403)

    def test_worker_task_recent_todo_qas(self):
        todo_task_0 = TodoFactory(
            project=self.project0, step=self.step)
        todo_task_1 = TodoFactory(
            project=self.project1, step=self.step)

        # Zero TodoQAs
        self._verify_worker_task_recent_todo_qas(
            self.task_0, None, True)

        todo_qa_task_0 = TodoQAFactory(todo=todo_task_0, approved=False)

        # Most recent TodoQA is todo_qa_task_0
        self._verify_worker_task_recent_todo_qas(
            self.task_0, todo_qa_task_0, True)

        self._verify_worker_task_recent_todo_qas(
            self.task_1, todo_qa_task_0, True)

        todo_qa_task_1 = TodoQAFactory(todo=todo_task_1, approved=False)

        # If available use the todo qa for the corresponding task.
        self._verify_worker_task_recent_todo_qas(
            self.task_0, todo_qa_task_0, True)

        self._verify_worker_task_recent_todo_qas(
            self.task_1, todo_qa_task_1, True)

        todo_qa_task_0.delete()

        # Most recent TodoQA is todo_qa_task_1
        self._verify_worker_task_recent_todo_qas(
            self.task_0, todo_qa_task_1, True)

        self._verify_worker_task_recent_todo_qas(
            self.task_1, todo_qa_task_1, True)

        # Can't make requests for projects in which you're uninvolved.
        bad_task = TaskFactory()
        todo_bad_task = TodoFactory(task=bad_task)
        todo_qa_bad_task = TodoQAFactory(todo=todo_bad_task, approved=False)
        self._verify_worker_task_recent_todo_qas(
            bad_task, todo_qa_bad_task, False)


class TodoTemplateEndpointTests(EndpointTestCase):
    def setUp(self):
        super().setUp()
        setup_models(self)
        self.worker = Worker.objects.get(user__username='test_user_6')
        self.request_client.login(username=self.worker.user.username,
                                  password='defaultpassword')
        self.todolist_template_list_url = reverse(
            'orchestra:todos:todolist_templates')
        self.todolist_template_detail_url_name = \
            'orchestra:todos:todolist_template'
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
        self.project2 = ProjectFactory()
        tasks = Task.objects.filter(assignments__worker=self.worker)
        self.task = tasks[0]
        self.task.project = self.project
        self.task.step = self.step
        self.task.save()

    def _todolist_template_data(
            self, slug, name, description, creator=None,
            todos="{'items': []}"):
        return {
            'slug': slug,
            'name': name,
            'description': description,
            'creator': creator,
            'todos': todos
        }

    def _verify_todolist_template_content(self, todolist_template,
                                          expected_todolist_template):
        todolist_template = dict(todolist_template)
        created_at = todolist_template.pop('created_at')
        todolist_template_id = todolist_template.pop('id')
        self.assertEqual(todolist_template, expected_todolist_template)
        self.assertGreater(len(created_at), 0)
        self.assertGreaterEqual(todolist_template_id, 0)

    def _verify_todolist_template_list(self, expected_todolist_templates):
        resp = self.request_client.get(self.todolist_template_list_url)
        self.assertEqual(resp.status_code, 200)
        length = len(expected_todolist_templates)
        data = load_encoded_json(resp.content)
        for todolist_template, expected_todolist_template in \
                zip(data[-length:], expected_todolist_templates):
            self._verify_todolist_template_content(
                todolist_template, expected_todolist_template)

    def _verify_todolist_template_creation(self):
        num_todolist_templates = TodoListTemplate.objects.all().count()
        resp = self.request_client.post(self.todolist_template_list_url, {
            'slug': self.todolist_template_slug,
            'name': self.todolist_template_name,
            'description': self.todolist_template_description})

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(TodoListTemplate.objects.all().count(),
                         num_todolist_templates + 1)
        todolist_template = load_encoded_json(resp.content)
        self._verify_todolist_template_content(
            todolist_template, self._todolist_template_data(
                self.todolist_template_slug,
                self.todolist_template_name,
                self.todolist_template_description))

    def test_todolist_template_update(self):
        todolist_template = TodoListTemplateFactory()
        updated_description = 'updated description'
        todolist_template_detail_url = reverse(
            self.todolist_template_detail_url_name,
            kwargs={'pk': todolist_template.id})
        resp = self.request_client.put(
            todolist_template_detail_url,
            json.dumps(self._todolist_template_data(
                todolist_template.slug,
                todolist_template.name,
                updated_description)),
            content_type='application/json')
        updated_todolist_template = TodoListTemplateSerializer(
            TodoListTemplate.objects.get(id=todolist_template.id)).data

        self.assertEqual(resp.status_code, 200)
        self._verify_todolist_template_content(
            updated_todolist_template, self._todolist_template_data(
                todolist_template.slug,
                todolist_template.name,
                updated_description))

    def test_todolist_template_list_create(self):
        self._verify_todolist_template_list([])
        self._verify_todolist_template_creation()
        self._verify_todolist_template_list(
            [self._todolist_template_data(
                self.todolist_template_slug,
                self.todolist_template_name,
                self.todolist_template_description)])

    def _verify_todo_content(self, todo, expected_todo):
        todo = dict(todo)
        created_at = todo.pop('created_at')
        todo_id = todo.pop('id')
        todo_skipped = bool(todo.pop('skipped_datetime', None))
        expected_skipped = bool(expected_todo.pop('skipped_datetime', None))

        self.assertEqual(todo_skipped, expected_skipped)
        self.assertEqual(todo, expected_todo)
        self.assertGreater(len(created_at), 0)
        self.assertGreaterEqual(todo_id, 0)

    def test_update_todos_from_todolist_template_success(self):
        num_todos = Todo.objects.all().count()
        update_todos_from_todolist_template_url = \
            reverse('orchestra:todos:update_todos_from_todolist_template')
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
        resp = self.request_client.post(
            update_todos_from_todolist_template_url,
            {
                'todolist_template': todolist_template.slug,
                'project': self.project.id,
                'step': self.step.slug
            })

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Todo.objects.all().count(), num_todos + 3)
        todos = load_encoded_json(resp.content)
        expected_todos = [
            _todo_data('todo child', False,
                       template=todolist_template.id,
                       parent_todo=todos[1]['id'],
                       project=self.project.id,
                       step=self.step.slug),
            _todo_data('todo parent', False,
                       template=todolist_template.id,
                       parent_todo=todos[2]['id'],
                       project=self.project.id,
                       step=self.step.slug),
            _todo_data(self.todolist_template_name,
                       False, template=todolist_template.id,
                       project=self.project.id,
                       step=self.step.slug),
        ]
        for todo, expected_todo in zip(todos, expected_todos):
            self._verify_todo_content(todo, expected_todo)

    def test_update_todos_from_todolist_template_missing_project_id(self):
        update_todos_from_todolist_template_url = \
            reverse('orchestra:todos:update_todos_from_todolist_template')
        todolist_template = TodoListTemplateFactory(
            slug=self.todolist_template_slug,
            name=self.todolist_template_name,
            description=self.todolist_template_description,
            todos={'items': []},
        )
        resp = self.request_client.post(
            update_todos_from_todolist_template_url,
            {
                'todolist_template': todolist_template.slug,
                'step': self.step.slug
            })

        self.assertEqual(resp.status_code, 403)

    def test_update_todos_from_todolist_template_invalid_project(self):
        update_todos_from_todolist_template_url = \
            reverse('orchestra:todos:update_todos_from_todolist_template')
        todolist_template = TodoListTemplateFactory(
            slug=self.todolist_template_slug,
            name=self.todolist_template_name,
            description=self.todolist_template_description,
            todos={'items': []},
        )
        resp = self.request_client.post(
            update_todos_from_todolist_template_url,
            {
                'todolist_template': todolist_template.slug,
                'project': self.project2.id,
                'step': self.step.id
            })

        self.assertEqual(resp.status_code, 403)

    def test_update_todos_from_todolist_template_invalid_todolist_template(
            self):
        update_todos_from_todolist_template_url = \
            reverse('orchestra:todos:update_todos_from_todolist_template')
        resp = self.request_client.post(
            update_todos_from_todolist_template_url,
            {
                'todolist_template': 'invalid-slug',
                'project': self.project.id,
                'step': self.step.id
            })

        self.assertEqual(resp.status_code, 400)

    def test_conditional_skip_remove_todos_from_template(self):
        update_todos_from_todolist_template_url = \
            reverse('orchestra:todos:update_todos_from_todolist_template')

        todolist_template = TodoListTemplateFactory(
            slug=self.todolist_template_slug,
            name=self.todolist_template_name,
            description=self.todolist_template_description,
            conditional_property_function={
                'path': 'orchestra.tests.test_todos'
                        '._get_test_conditional_props'
            },
            todos={'items': [
                {
                    'id': 1,
                    'description': 'todo parent 1',
                    'project': self.project.id,
                    'items': [{
                        'id': 2,
                        'description': 'todo child 1',
                        'project': self.project.id,
                        'items': []
                    }],
                    'remove_if': [{
                        'prop1': {
                            'operator': '==',
                            'value': True
                        }
                    }]
                }, {
                    'id': 3,
                    'description': 'todo parent 2',
                    'project': self.project.id,
                    'items': [{
                        'id': 4,
                        'description': 'todo child 2',
                        'project': self.project.id,
                        'items': [],
                        'skip_if': [{
                            'prop2': {
                                'operator': '!=',
                                'value': True
                            }
                        }]
                    }]
                }]},
        )
        resp = self.request_client.post(
            update_todos_from_todolist_template_url,
            {
                'todolist_template': todolist_template.slug,
                'project': self.project.id,
                'step': self.step.slug
            })
        self.assertEqual(resp.status_code, 200)
        todos = load_encoded_json(resp.content)

        expected_todos = [
            _todo_data('todo child 2', False,
                       template=todolist_template.id,
                       parent_todo=todos[1]['id'],
                       skipped_datetime=timezone.now(),
                       project=self.project.id,
                       step=self.step.slug),
            _todo_data('todo parent 2', False,
                       template=todolist_template.id,
                       parent_todo=todos[2]['id'],
                       project=self.project.id,
                       step=self.step.slug),
            _todo_data(self.todolist_template_name,
                       False, template=todolist_template.id,
                       project=self.project.id,
                       step=self.step.slug),
        ]
        for todo, expected_todo in zip(todos, expected_todos):
            self._verify_todo_content(todo, expected_todo)


class TodoListTemplatesImportExportTests(OrchestraTransactionTestCase):

    def setUp(self):
        super().setUp()
        setup_models(self)
        self.worker = Worker.objects.get(user__username='test_user_6')
        self.worker.user.is_staff = True
        self.worker.user.save()
        self.request_client.login(username=self.worker.user.username,
                                  password='defaultpassword')
        self.full_todo_list_template = TodoListTemplateFactory(
            slug='full-template-slug',
            name='Full template name',
            description='Full template description',
            conditional_property_function={
                'path': 'orchestra.tests.test_todos'
                        '._get_test_conditional_props'
            },
            todos=TODO_TEMPLATE_NESTED_TODOS
        )
        self.empty_todo_list_template = TodoListTemplateFactory(
            slug='empty-template-slug',
            name='Empty template name',
            description='Empty template description',
            conditional_property_function={
                'path': 'orchestra.tests.test_todos'
                        '._get_test_conditional_props'
            },
            todos={}
        )

        self.import_url_name = (
            'orchestra:todos:import_todo_list_template_from_spreadsheet')
        self.template_admin_name = 'admin:orchestra_todolisttemplate_change'
        self.export_url_name = 'admin:orchestra_todolisttemplate_actions'

    @patch('orchestra.todos.import_export._upload_csv_to_google')
    def test_export_spreadsheet(self, mock_upload):
        mock_upload.return_value = 'https://redirect.com/the_spreadsheet'
        export_url = reverse(
            self.export_url_name,
            kwargs={'pk': self.full_todo_list_template.id,
                    'tool': 'export_spreadsheet'})
        response = self.request_client.get(export_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, 'https://redirect.com/the_spreadsheet')
        self.assertEqual(mock_upload.call_count, 1)
        title_prefix = (mock_upload.call_args[0][0]
                        [:len(self.full_todo_list_template.name) + 2])
        self.assertEqual(
            title_prefix,
            '{} -'.format(self.full_todo_list_template.name))
        with open(mock_upload.call_args[0][1].name, 'r') as exported_file:
            lines = ''.join(exported_file.readlines())
            # The JSON encoding of properties is nondeterministic in order.
            lines = lines.replace(
                '"[{""prop"": {""operator"": ""=="", ""value"": true}}]"',
                'PROPREPLACED')
            lines = lines.replace(
                '"[{""prop"": {""value"": true, ""operator"": ""==""}}]"',
                'PROPREPLACED')
            correct_text = TODO_TEMPLATE_GOOD_CSV_TEXT.replace(
                '"[{""prop"": {""value"": true, ""operator"": ""==""}}]"',
                'PROPREPLACED')
            self.assertEqual(lines, correct_text)

    @patch('orchestra.todos.import_export.get_google_spreadsheet_as_csv')
    def test_import_spreadsheet(self, mock_get_spreadsheet):
        mock_get_spreadsheet.side_effect = self._fake_get_spreadsheet(
            TODO_TEMPLATE_GOOD_CSV_TEXT)

        import_url = reverse(
            self.import_url_name,
            kwargs={'pk': self.empty_todo_list_template.id})
        admin_url = reverse(
            self.template_admin_name,
            kwargs={'object_id': self.empty_todo_list_template.id})

        response = self.request_client.get(import_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            'orchestra/import_todo_list_template_from_spreadsheet.html')
        self.assertEqual(mock_get_spreadsheet.call_count, 0)

        # Before import, the empty_todo_list_template should have no
        # template to-dos. After import, it should have the same
        # to-dos as full_todo_list_template (the CSV we load from is
        # equivalent to full_todo_list_template's to-dos).
        self.empty_todo_list_template.refresh_from_db()
        self.assertEqual(self.empty_todo_list_template.todos, {})
        self.assertEqual(
            TodoListTemplateImportRecord.objects.all().count(),
            0)
        response = self.request_client.post(
            import_url,
            {'spreadsheet_url': 'https://the-spreadsheet.com/url'})
        self.assertRedirects(
            response, admin_url,
            target_status_code=403)  # User doesn't have model access.
        self.assertEqual(mock_get_spreadsheet.call_count, 1)
        self.assertEqual(mock_get_spreadsheet.call_args[0][0],
                         'https://the-spreadsheet.com/url')
        self.empty_todo_list_template.refresh_from_db()

        # Walk the to-do tree, moving IDs (which won't be equal, but
        # should be unique) into a set. Ensure the rest of the fields
        # are equivalent after setting missing `skip_id`/`remove_if`
        # to `[]`.
        def recursively_pop_ids(todos, id_set):
            id = todos.pop('id', None)
            if id is not None:
                id_set.add(id)
            todos.setdefault('remove_if', [])
            todos.setdefault('skip_if', [])
            for item in todos.get('items', []):
                recursively_pop_ids(item, id_set)
        empty_ids = set()
        full_ids = set()
        empty_todos = copy.deepcopy(self.empty_todo_list_template.todos)
        full_todos = copy.deepcopy(self.full_todo_list_template.todos)
        recursively_pop_ids(empty_todos, empty_ids)
        recursively_pop_ids(full_todos, full_ids)
        self.assertEqual(len(empty_ids), 7)
        self.assertEqual(len(empty_ids), len(full_ids))
        self.assertEqual(empty_todos, full_todos)

        self.assertEqual(
            TodoListTemplateImportRecord.objects.all().count(),
            1)
        import_record = TodoListTemplateImportRecord.objects.first()
        self.assertEqual(import_record.todo_list_template.id,
                         self.empty_todo_list_template.id)
        self.assertEqual(import_record.importer.id,
                         self.worker.user.id)
        self.assertEqual(import_record.import_url,
                         'https://the-spreadsheet.com/url')

    @patch('orchestra.todos.import_export.get_google_spreadsheet_as_csv')
    def test_import_spreadsheet_errors(self, mock_get_spreadsheet):
        import_url = reverse(
            self.import_url_name,
            kwargs={'pk': self.empty_todo_list_template.id})

        mock_get_spreadsheet.side_effect = self._fake_get_spreadsheet(
            TODO_TEMPLATE_BAD_HEADER_CSV_TEXT)
        response = self.request_client.post(
            import_url,
            {'spreadsheet_url': 'https://the-spreadsheet.com/url'})
        self.assertEqual(response.status_code, 200)  # We didn't redirect.
        self.assertEqual(mock_get_spreadsheet.call_count, 1)
        self.assertRegex(response.content.decode('utf-8'),
                         'Error: Unexpected header:')
        mock_get_spreadsheet.reset_mock()

        mock_get_spreadsheet.side_effect = self._fake_get_spreadsheet(
            TODO_TEMPLATE_TWO_ENTRIES_CSV_TEXT)
        response = self.request_client.post(
            import_url,
            {'spreadsheet_url': 'https://the-spreadsheet.com/url'})
        self.assertEqual(response.status_code, 200)  # We didn't redirect.
        self.assertEqual(mock_get_spreadsheet.call_count, 1)
        self.assertRegex(response.content.decode('utf-8'),
                         'Error: More than one text entry in row 0: ')
        mock_get_spreadsheet.reset_mock()

        mock_get_spreadsheet.side_effect = self._fake_get_spreadsheet(
            TODO_TEMPLATE_INVALID_PARENT_CSV_TEXT)
        response = self.request_client.post(
            import_url,
            {'spreadsheet_url': 'https://the-spreadsheet.com/url'})
        self.assertEqual(response.status_code, 200)  # We didn't redirect.
        self.assertEqual(mock_get_spreadsheet.call_count, 1)
        self.assertRegex(response.content.decode('utf-8'),
                         'Error: Row 1 has skipped some columns in depth: ')
        mock_get_spreadsheet.reset_mock()

        # Nothing should have been created/updated since every import
        # failed.
        self.empty_todo_list_template.refresh_from_db()
        self.assertEqual(self.empty_todo_list_template.todos, {})
        self.assertEqual(
            TodoListTemplateImportRecord.objects.all().count(),
            0)

    def _fake_get_spreadsheet(self, csv_text):
        def fake_get_spreadsheet(spreadsheet_url, reader):
            return reader(
                StringIO(csv_text), dialect=csv.excel)
        return fake_get_spreadsheet
