import json

from django.utils import timezone
from dateutil.parser import parse
from django.core.urlresolvers import reverse

from orchestra.models import Task
from orchestra.models import Todo
from orchestra.models import TodoQA
from orchestra.models import TodoListTemplate
from orchestra.models import Worker
from orchestra.project_api.serializers import TimeEntrySerializer
from orchestra.tests.helpers import EndpointTestCase
from orchestra.tests.helpers.fixtures import TaskFactory
from orchestra.tests.helpers.fixtures import TodoFactory
from orchestra.tests.helpers.fixtures import TodoQAFactory
from orchestra.tests.helpers.fixtures import TodoListTemplateFactory
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.todos.serializers import TodoSerializer
from orchestra.todos.serializers import TodoQASerializer
from orchestra.todos.serializers import TodoListTemplateSerializer
from orchestra.utils.load_json import load_encoded_json


def _todo_data(task, description, completed,
               skipped_datetime=None, start_by=None,
               due=None, parent_todo=None, template=None,
               activity_log=str({'actions': []}), qa=None):
    return {
        'task': task.id,
        'completed': completed,
        'description': description,
        'template': template,
        'parent_todo': parent_todo,
        'start_by_datetime': start_by,
        'due_datetime': due,
        'activity_log': activity_log,
        'skipped_datetime': skipped_datetime,
        'qa': qa
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
        self.tasks = Task.objects.filter(
            assignments__worker=self.worker)
        self.task_0 = self.tasks[0]
        self.task_1 = self.tasks[1]
        self.todo = TodoFactory(task=self.task_0)
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
        todo = TodoFactory()
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
        todo_task_0 = TodoFactory(task=self.task_0)
        todo_task_1 = TodoFactory(task=self.task_1)

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
                'items': [{
                    'id': 2,
                    'description': 'todo child',
                    'items': []
                }]
            }]},
        )
        resp = self.request_client.post(
            update_todos_from_todolist_template_url,
            {
                'todolist_template': todolist_template.slug,
                'task': self.task.id,
            })

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Todo.objects.all().count(), num_todos + 3)
        todos = load_encoded_json(resp.content)
        expected_todos = [
            _todo_data(self.task, 'todo child', False,
                       template=todolist_template.id,
                       parent_todo=todos[1]['id']),
            _todo_data(self.task, 'todo parent', False,
                       template=todolist_template.id,
                       parent_todo=todos[2]['id']),
            _todo_data(self.task, self.todolist_template_name,
                       False, template=todolist_template.id),
        ]
        for todo, expected_todo in zip(todos, expected_todos):
            self._verify_todo_content(todo, expected_todo)

    def test_update_todos_from_todolist_template_missing_task_id(self):
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
                'todolist_template': todolist_template.slug
            })

        self.assertEqual(resp.status_code, 403)

    def test_update_todos_from_todolist_template_invalid_task(self):
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
                'task': 999999999999999,
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
                'task': self.task.id,
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
                    'items': [{
                        'id': 2,
                        'description': 'todo child 1',
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
                    'items': [{
                        'id': 4,
                        'description': 'todo child 2',
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
                'task': self.task.id,
            })
        self.assertEqual(resp.status_code, 200)
        todos = load_encoded_json(resp.content)

        expected_todos = [
            _todo_data(self.task, 'todo child 2', False,
                       template=todolist_template.id,
                       parent_todo=todos[1]['id'],
                       skipped_datetime=timezone.now()),
            _todo_data(self.task, 'todo parent 2', False,
                       template=todolist_template.id,
                       parent_todo=todos[2]['id']),
            _todo_data(self.task, self.todolist_template_name,
                       False, template=todolist_template.id),
        ]
        for todo, expected_todo in zip(todos, expected_todos):
            self._verify_todo_content(todo, expected_todo)
