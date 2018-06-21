import json

from dateutil.parser import parse
from django.core.urlresolvers import reverse

from orchestra.models import Task
from orchestra.models import Todo
from orchestra.models import TodoListTemplate
from orchestra.models import Worker
from orchestra.project_api.serializers import TimeEntrySerializer
from orchestra.tests.helpers import EndpointTestCase
from orchestra.tests.helpers.fixtures import TaskFactory
from orchestra.tests.helpers.fixtures import TodoFactory
from orchestra.tests.helpers.fixtures import TodoListTemplateFactory
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.todos.serializers import TodoSerializer
from orchestra.todos.serializers import TodoListTemplateSerializer
from orchestra.utils.load_json import load_encoded_json


def _todo_data(task, description, completed,
               skipped_datetime=None, start_by=None, due=None):
    return {
        'task': task.id,
        'completed': completed,
        'description': description,
        'start_by_datetime': start_by,
        'due_datetime': due,
        'skipped_datetime': skipped_datetime
    }


class TimeEntriesEndpointTests(EndpointTestCase):

    def setUp(self):
        super().setUp()
        setup_models(self)
        self.worker = Worker.objects.get(user__username='test_user_6')
        self.request_client.login(username=self.worker.user.username,
                                  password='defaultpassword')
        self.list_create_url = reverse('orchestra:todos:todos')
        self.list_details_url_name = 'orchestra:todos:todo'
        self.tasks = Task.objects.filter(assignments__worker=self.worker)
        self.task = self.tasks[0]
        self.todo_description = 'Let us do this'
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
                                       {'project': project_id})
        if success:
            self.assertEqual(resp.status_code, 200)
            data = load_encoded_json(resp.content)
            for todo, expected_todo in zip(data, expected_todos):
                self._verify_todo_content(todo, expected_todo)
        else:
            self.assertEqual(resp.status_code, 403)

    def _verify_todo_creation(self, task, success):
        num_todos = Todo.objects.all().count()
        resp = self.request_client.post(self.list_create_url, {
            'task': task.id,
            'description': self.todo_description})
        if success:
            self.assertEqual(resp.status_code, 201)
            self.assertEqual(Todo.objects.all().count(), num_todos + 1)
            todo = load_encoded_json(resp.content)
            self._verify_todo_content(
                todo, _todo_data(task, self.todo_description, False))
        else:
            self.assertEqual(resp.status_code, 403)
            self.assertEqual(Todo.objects.all().count(), num_todos)

    def _verify_todo_update(self, todo, success):
        description = 'new description'
        list_details_url = reverse(
            self.list_details_url_name,
            kwargs={'pk': todo.id})
        resp = self.request_client.put(
            list_details_url,
            json.dumps(_todo_data(todo.task, description, True)),
            content_type='application/json')
        updated_todo = TodoSerializer(Todo.objects.get(id=todo.id)).data
        if success:
            self.assertEqual(resp.status_code, 200)
            self._verify_todo_content(
                updated_todo, _todo_data(todo.task, description, True))
        else:
            self.assertEqual(resp.status_code, 403)
            self.assertNotEqual(updated_todo['description'], description)

    def test_todos_list_create(self):
        self._verify_todos_list(self.task.project.id, [], True)
        self._verify_todo_creation(self.task, True)
        self._verify_todos_list(self.task.project.id,
                                [_todo_data(
                                    self.task, self.todo_description, False)],
                                True)

    def test_todos_list_create_permissions(self):
        # Can't make requests for projects in which you're uninvolved.
        task = TaskFactory()
        self._verify_todos_list(task.project.id, [], False)
        self._verify_todo_creation(task, False)

    def test_todo_details_and_permissions(self):
        # You should be able to update Todos for projects in which
        # you're involved, and not for other projects.
        good_todo = TodoFactory(task=self.task)
        self._verify_todo_update(good_todo, True)
        bad_todo = TodoFactory()
        self._verify_todo_update(bad_todo, False)

    def test_create_todo_with_start_by_datetime(self):
        START_DESCRIPTION = 'Start soon'

        start_by_todo = TodoFactory(
            task=self.task,
            start_by_datetime=self.deadline,
            description=START_DESCRIPTION)

        self._verify_todos_list(self.task.project.id, [
            _todo_data(
                start_by_todo.task,
                START_DESCRIPTION,
                False,
                None,
                self.deadline.strftime('%Y-%m-%dT%H:%M:%SZ'),
                None)
        ], True)

    def test_create_todo_with_due_datetime(self):
        DUE_DESCRIPTION = 'Due soon'

        due_todo = TodoFactory(
            task=self.task,
            due_datetime=self.deadline,
            description=DUE_DESCRIPTION)

        self._verify_todos_list(self.task.project.id, [
            _todo_data(
                due_todo.task,
                DUE_DESCRIPTION,
                False,
                None,
                None,
                self.deadline.strftime('%Y-%m-%dT%H:%M:%SZ')),
        ], True)


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
        self.tasks = Task.objects.filter(assignments__worker=self.worker)
        self.task = self.tasks[0]

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
        data = load_encoded_json(resp.content)
        for todolist_template, expected_todolist_template in \
                zip(data, expected_todolist_templates):
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
        parent_todo = todo.pop('parent_todo')
        parent_todo = todo.pop('template')
        self.assertEqual(todo, expected_todo)
        self.assertGreater(len(created_at), 0)
        self.assertGreaterEqual(todo_id, 0)

    def test_add_todos_from_todolist_template_success(self):
        num_todos = Todo.objects.all().count()
        add_todos_from_todolist_template_url = \
            reverse('orchestra:todos:add_todos_from_todolist_template')
        todolist_template = TodoListTemplateFactory(
            slug=self.todolist_template_slug,
            name=self.todolist_template_name,
            description=self.todolist_template_description,
            todos={'items': [{
                'id': 1,
                'description': 'todo parent',
                'items': [{
                    'id': 2,
                    'description': 'todo child',
                    'items': []
                }]
            }]},
        )
        resp = self.request_client.post(
            add_todos_from_todolist_template_url,
            {
                'todolist_template': todolist_template.id,
                'task': self.task.id,
            })

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Todo.objects.all().count(), num_todos + 3)
        todos = load_encoded_json(resp.content)
        expected_todos = [
            _todo_data(self.task, 'todo child', False),
            _todo_data(self.task, 'todo parent', False),
            _todo_data(self.task, self.todolist_template_name, False),
        ]
        for todo, expected_todo in zip(todos, expected_todos):
            self._verify_todo_content(todo, expected_todo)

    def test_add_todos_from_todolist_template_forbidden(self):
        add_todos_from_todolist_template_url = \
            reverse('orchestra:todos:add_todos_from_todolist_template')
        todolist_template = TodoListTemplateFactory(
            slug=self.todolist_template_slug,
            name=self.todolist_template_name,
            description=self.todolist_template_description,
            todos={'items': []},
        )
        resp = self.request_client.post(
            add_todos_from_todolist_template_url,
            {
                'todolist_template': todolist_template.id
            })

        self.assertEqual(resp.status_code, 403)
