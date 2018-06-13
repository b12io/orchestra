import json

from dateutil.parser import parse
from django.core.urlresolvers import reverse

from orchestra.models import Task
from orchestra.models import Todo
from orchestra.models import ChecklistTemplate
from orchestra.models import Worker
from orchestra.project_api.serializers import TimeEntrySerializer
from orchestra.tests.helpers import EndpointTestCase
from orchestra.tests.helpers.fixtures import TaskFactory
from orchestra.tests.helpers.fixtures import TodoFactory
# from orchestra.tests.helpers.fixtures import ChecklistTemplateFactory
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.todos.serializers import TodoSerializer
from orchestra.utils.load_json import load_encoded_json


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

    def _todo_data(
            self, task, description, completed,
            skipped=False, start_by=None, due=None):
        return {
            'task': task.id,
            'completed': completed,
            'description': description,
            'start_by_datetime': start_by,
            'due_datetime': due,
            'skipped': skipped
        }

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
                todo, self._todo_data(task, self.todo_description, False))
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
            json.dumps(self._todo_data(todo.task, description, True)),
            content_type='application/json')
        updated_todo = TodoSerializer(Todo.objects.get(id=todo.id)).data
        if success:
            self.assertEqual(resp.status_code, 200)
            self._verify_todo_content(
                updated_todo, self._todo_data(todo.task, description, True))
        else:
            self.assertEqual(resp.status_code, 403)
            self.assertNotEqual(updated_todo['description'], description)

    def test_todos_list_create(self):
        self._verify_todos_list(self.task.project.id, [], True)
        self._verify_todo_creation(self.task, True)
        self._verify_todos_list(self.task.project.id,
                                [self._todo_data(
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
            self._todo_data(
                start_by_todo.task,
                START_DESCRIPTION,
                False,
                False,
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
            self._todo_data(
                due_todo.task,
                DUE_DESCRIPTION,
                False,
                False,
                None,
                self.deadline.strftime('%Y-%m-%dT%H:%M:%SZ')),
        ], True)


class ChecklistTemplateEndpointTests(EndpointTestCase):

    def setUp(self):
        super().setUp()
        setup_models(self)
        self.worker = Worker.objects.get(user__username='test_user_6')
        self.request_client.login(username=self.worker.user.username,
                                  password='defaultpassword')
        self.checklist_template_list_url = reverse(
            'orchestra:todos:checklists')
        self.checklist_template_detail_url_name = 'orchestra:todos:checklist'
        self.checklist_template_slug = 'test_checklist_template_slug'
        self.checklist_template_name = 'test_checklist_template_name'
        self.checklist_template_description = \
            'test_checklist_template_description'

    def _checklist_template_data(
            self, slug, name, description, creator=None,
            todos="{'list': []}"):
        return {
            'slug': slug,
            'name': name,
            'description': description,
            'creator': creator,
            'todos': todos
        }

    def _verify_checklist_template_content(self, checklist_template,
                                           expected_checklist_template):
        checklist_template = dict(checklist_template)
        created_at = checklist_template.pop('created_at')
        checklist_template_id = checklist_template.pop('id')
        self.assertEqual(checklist_template, expected_checklist_template)
        self.assertGreater(len(created_at), 0)
        self.assertGreaterEqual(checklist_template_id, 0)

    def _verify_checklist_template_list(self, expected_checklist_templates,
                                        success):
        resp = self.request_client.get(self.checklist_template_list_url)
        if success:
            self.assertEqual(resp.status_code, 200)
            data = load_encoded_json(resp.content)
            for checklist_template, expected_checklist_template in \
                    zip(data, expected_checklist_templates):
                self._verify_checklist_template_content(
                    checklist_template, expected_checklist_template)
        else:
            self.assertEqual(resp.status_code, 403)

    def _verify_checklist_template_creation(self, success):
        num_checklist_templates = ChecklistTemplate.objects.all().count()
        resp = self.request_client.post(self.checklist_template_list_url, {
            'slug': self.checklist_template_slug,
            'name': self.checklist_template_name,
            'description': self.checklist_template_description})

        if success:
            self.assertEqual(resp.status_code, 201)
            self.assertEqual(ChecklistTemplate.objects.all().count(),
                             num_checklist_templates + 1)
            checklist_template = load_encoded_json(resp.content)
            self._verify_checklist_template_content(
                checklist_template, self._checklist_template_data(
                    self.checklist_template_slug,
                    self.checklist_template_name,
                    self.checklist_template_description))
        else:
            self.assertEqual(resp.status_code, 403)
            self.assertEqual(ChecklistTemplate.objects.all().count(),
                             num_checklist_templates)

    def _verify_checklist_template_update(self, checklist_template, success):
        updated_description = 'updated description'
        num_checklist_templates = ChecklistTemplate.objects.all().count()
        checklist_template_detail_url = reverse(
            self.checklist_template_detail_url_name,
            kwargs={'pk': checklist_template.id})
        resp = self.request_client.put(
            self.checklist_template_detail_url,
            json.dumps(self._checklist_template_data(
                checklist_template.slug,
                checklist_template.name,
                updated_description)),
            content_type='application/json')
        updated_checklist_template = ChecklistTemplateSerializer(
            ChecklistTemplate.objects.get(id=checklist_template.id)).data

        if success:
            self.assertEqual(resp.status_code, 200)
            self._verify_checklist_template_content(
                updated_checklist_template, self._checklist_template_data(
                    checklist_template.slug,
                    checklist_template.name,
                    updated_description))
        else:
            self.assertEqual(resp.status_code, 403)
            self.assertNotEqual(
                updated_checklist_template['description'], updated_description)

    def test_checklist_template_list_create(self):
        self._verify_checklist_template_list([], True)
        self._verify_checklist_template_creation(True)
        self._verify_checklist_template_list(
            [self._checklist_template_data(
                self.checklist_template_slug,
                self.checklist_template_name,
                self.checklist_template_description)],
            True)
