import json
import datetime
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
from django.test import override_settings
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIClient

from orchestra.google_apps.service import Service
from orchestra.models import Project
from orchestra.models import Task
from orchestra.models import Todo
from orchestra.models import TaskAssignment
from orchestra.models import TimeEntry
from orchestra.models import Worker
from orchestra.models import WorkerCertification
from orchestra.todos.serializers import BulkTodoSerializer
from orchestra.project_api.api import MalformedDependencyException
from orchestra.project_api.api import get_workflow_steps
from orchestra.project_api.api import get_project_information
from orchestra.project_api.auth import OrchestraProjectAPIAuthentication
from orchestra.project_api.auth import SignedUser
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers import EndpointTestCase
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.tests.helpers.fixtures import StepFactory
from orchestra.tests.helpers.fixtures import ProjectFactory
from orchestra.tests.helpers.fixtures import TodoFactory
from orchestra.tests.helpers.fixtures import WorkflowVersionFactory
from orchestra.tests.helpers.google_apps import mock_create_drive_service
from orchestra.utils.load_json import load_encoded_json
from orchestra.utils.task_lifecycle import get_new_task_assignment


class ProjectAPITestCase(OrchestraTestCase):

    def setUp(self):
        super().setUp()
        setup_models(self)
        self.api_client = APIClient(enforce_csrf_checks=True)
        self.api_client.force_authenticate(user=SignedUser())

    def test_project_details_url(self):
        project = Project.objects.all()[0]
        response = self.api_client.post(
            reverse('orchestra:orchestra:project_details_url'),
            {'project_id': project.id},
            format='json')
        self.assertEqual(response.status_code, 200)
        returned = load_encoded_json(response.content)
        project_details_url = returned.get('project_details_url')
        self.assertEqual(project_details_url,
                         ('http://testserver/orchestra/app/project/%s' %
                          project.id))

        response = self.api_client.post(
            '/orchestra/api/project/project_details_url/',
            {},
            format='json')

        self.ensure_response(response,
                             {'error': 400,
                              'message': 'project_id parameter is missing'},
                             400)

    def test_project_information(self):
        project = self.projects['base_test_project']
        response = self.api_client.post(
            '/orchestra/api/project/project_information/',
            {'project_ids': [project.id]},
            format='json')
        self.assertEqual(response.status_code, 200)
        returned = load_encoded_json(response.content)

        self._delete_keys(returned[str(project.id)])
        for item in returned.values():
            del item['tasks']['step1']['project']
            del (item['tasks']['step1']['assignments'][0]
                     ['iterations'][0]['assignment'])

        expected = {
            'project': {
                'task_class': 1,
                'workflow_slug': 'w1',
                'workflow_version_slug': 'test_workflow',
                'project_data': {},
                'team_messages_url': None,
                'priority': 0,
                'status': 0
            },
            'tasks': {
                'step1': {
                    'assignments': [{
                        'status': 'Submitted',
                        'in_progress_task_data': {'test_key': 'test_value'},
                        'worker': {
                            'username': self.workers[0].user.username,
                            'first_name': self.workers[0].user.first_name,
                            'last_name': self.workers[0].user.last_name,
                            'slack_username':
                                self.workers[0].slack_username,
                            'slack_user_id':
                                self.workers[0].slack_user_id
                        },
                        'iterations': [{
                            'status': 'Requested Review',
                            'submitted_data': {'test_key': 'test_value'},
                        }],
                        'recorded_work_time': 30*60,
                    }],
                    'latest_data': {
                        'test_key': 'test_value'
                    },
                    'status': 'Pending Review',
                    'step_slug': 'step1',
                }
            },
            'steps': [
                {'slug': 'step1',
                 'description': 'The longer description of the first step',
                 'is_human': True,
                 'name': 'The first step'},
                {'slug': 'step2',
                 'description': 'The longer description of the second step',
                 'is_human': True,
                 'name': 'The second step'},
                {'slug': 'step3',
                 'description': 'The longer description of the third step',
                 'is_human': True,
                 'name': 'The third step'}
            ]
        }

        self.assertEqual(returned[str(project.id)], expected)

        response = self.api_client.post(
            '/orchestra/api/project/project_information/',
            {'project_ids': [-1]},
            format='json')
        self.assertEqual(load_encoded_json(response.content), {})

        # Getting project info without a project_ids should fail.
        response = self.api_client.post(
            '/orchestra/api/project/project_information/',
            {'project_id': [project.id]},  # Typo.
            format='json')
        msg = 'project_ids is required'
        self.ensure_response(response,
                             {'error': 400, 'message': msg}, 400)

        # Retrieve the third project, which has no task assignments.
        project_id = self.projects['no_task_assignments'].id
        response = self.api_client.post(
            '/orchestra/api/project/project_information/',
            {'project_ids': [project_id]},
            format='json')
        returned = load_encoded_json(response.content)
        for key in ('id', 'project', 'start_datetime'):
            del returned[str(project_id)]['tasks']['step1'][key]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(returned[str(project_id)]['tasks'], {
            'step1': {
                'assignments': [],
                'latest_data': None,
                'status': 'Awaiting Processing',
                'step_slug': 'step1'
            }
        })

    def test_project_assignment_recorded_time(self):
        project = self.projects['base_test_project']
        worker = self.workers[0]

        task = self.tasks['review_task']
        assignment = TaskAssignment.objects.filter(
            worker=worker, task=task).first()
        other_assignment = get_new_task_assignment(
            worker, Task.Status.AWAITING_PROCESSING)

        # create 3 time entries
        TimeEntry.objects.create(
            worker=self.workers[0],
            date=datetime.datetime.now().date(),
            time_worked=datetime.timedelta(hours=1),
            assignment=assignment)
        TimeEntry.objects.create(
            worker=self.workers[0],
            date=datetime.datetime.now().date(),
            time_worked=datetime.timedelta(hours=1),
            assignment=other_assignment)
        TimeEntry.objects.create(
            worker=self.workers[0],
            date=datetime.datetime.now().date(),
            time_worked=datetime.timedelta(minutes=15),
            assignment=assignment)

        response = self.api_client.post(
            '/orchestra/api/project/project_information/',
            {'project_ids': [project.id]},
            format='json')
        returned = load_encoded_json(response.content)
        returned_task = returned[str(project.id)]['tasks']
        returned_assignment = returned_task['step1']['assignments'][0]
        recorded_time = returned_assignment['recorded_work_time']
        self.assertEqual(recorded_time, 105*60)  # 1:15 + 0:30

    def test_get_workflow_steps(self):
        # See orchestra.tests.helpers.fixtures for workflow description
        steps = get_workflow_steps('w3', 'crazy_workflow')
        slugs = [step['slug'] for step in steps]

        self.assertTrue(slugs.index('stepC') > slugs.index('stepA'))
        self.assertTrue(slugs.index('stepC') > slugs.index('stepB'))
        self.assertTrue(slugs.index('stepD') > slugs.index('stepA'))
        self.assertTrue(slugs.index('stepD') > slugs.index('stepB'))
        self.assertTrue(slugs.index('stepE') > slugs.index('stepC'))
        self.assertTrue(slugs.index('stepE') > slugs.index('stepD'))
        self.assertTrue(slugs.index('stepF') > slugs.index('stepE'))
        self.assertTrue(slugs.index('stepG') > slugs.index('stepF'))
        self.assertTrue(slugs.index('stepH') > slugs.index('stepF'))

        steps = get_workflow_steps('w4', 'erroneous_workflow_1')

        with self.assertRaises(MalformedDependencyException):
            steps = get_workflow_steps('w5', 'erroneous_workflow_2')

    def test_get_project_information(self):
        projects = Project.objects.all()[:2]
        projects_info = get_project_information(
            [p.pk for p in projects])
        a_project_info_key = list(projects_info.keys())[0]
        a_project_info = projects_info[a_project_info_key]
        self.assertTrue(isinstance(a_project_info['project'], dict))
        self.assertTrue(isinstance(a_project_info['tasks'], dict))
        self.assertTrue(isinstance(a_project_info['steps'], list))

    @patch.object(
        Service, '_create_drive_service',
        new=mock_create_drive_service)
    def test_create_project(self):
        tasks_awaiting_processing = (
            Task.objects
            .filter(status=Task.Status.AWAITING_PROCESSING)
            .count())
        response = self.api_client.post(
            '/orchestra/api/project/create_project/',
            {'workflow_slug': 'w1',
             'workflow_version_slug': 'test_workflow',
             'description': 'short test description',
             'priority': 10,
             'task_class': 'real',
             'project_data': {}},
            format='json')
        self.assertEqual(response.status_code, 200)

        self.assertEqual((Task.objects
                          .filter(status=Task.Status.AWAITING_PROCESSING)
                          .count()),
                         tasks_awaiting_processing + 1)

        # Creating a 'training' project should set task_class correctly.
        response = self.api_client.post(
            '/orchestra/api/project/create_project/',
            {'workflow_slug': 'w1',
             'workflow_version_slug': 'test_workflow',
             'description': 'short test description',
             'priority': 10,
             'task_class': 'training',
             'project_data': {}},
            format='json')
        self.assertEqual(response.status_code, 200)
        project_id = load_encoded_json(response.content)['project_id']
        self.assertEqual(Project.objects.get(id=project_id).task_class,
                         WorkerCertification.TaskClass.TRAINING)

        # Creating a project with missing parameters should fail.
        response = self.api_client.post(
            '/orchestra/api/project/create_project/',
            {'workflow_slug': 'w1'},
            format='json')
        self.ensure_response(response,
                             {'error': 400,
                              'message': 'One of the parameters is missing'},
                             400)

    def test_workflow_types(self):
        response = self.api_client.get(
            '/orchestra/api/project/workflow_types/', format='json')
        self.assertEqual(response.status_code, 200)

        workflows = load_encoded_json(response.content)['workflows']
        workflows = dict(workflows)
        self.assertEqual(
            workflows,
            {
                workflow_slug: {
                    'name': workflow.name,
                    'versions': {
                        v.slug: {
                            'name': v.name,
                            'description': v.description,
                        }
                        for v in workflow.versions.all()
                    }
                }
                for workflow_slug, workflow in self.workflows.items()
            }
        )

    def _make_assign_worker_task_request(self, worker_id,
                                         task_id, success=True):
        response = self.api_client.post(
            '/orchestra/api/project/assign_worker_to_task/',
            {
                'worker_id': worker_id,
                'task_id': task_id,
            },
            format='json')
        self.assertEqual(response.status_code, 200)
        data = load_encoded_json(response.content)
        self.assertEqual(data['success'], success)
        return data

    def test_assign_worker_to_task(self):
        worker = self.workers[0]

        # We should be able to assign to an unassigned task
        task = self.tasks['awaiting_processing']
        query = TaskAssignment.objects.filter(worker=worker, task=task)
        self.assertFalse(query.exists())
        data = self._make_assign_worker_task_request(worker.id, task.id)
        self.assertTrue(query.exists())
        query.delete()

        # Nonsense arguments
        task = self.tasks['awaiting_processing']
        query = TaskAssignment.objects.filter(worker=worker, task=task)
        self.assertFalse(query.exists())
        data = self._make_assign_worker_task_request(None, None, success=False)
        self.assertTrue('error' in data['errors'])
        self.assertFalse(query.exists())

        # Invalid Worker
        task = self.tasks['awaiting_processing']
        query = TaskAssignment.objects.filter(worker=worker, task=task)
        self.assertFalse(query.exists())
        data = self._make_assign_worker_task_request(
            -1, task.id, success=False)
        self.assertTrue('error' in data['errors'])
        self.assertFalse(query.exists())

        # Invalid Task
        task = self.tasks['awaiting_processing']
        query = TaskAssignment.objects.filter(worker=worker, task=task)
        self.assertFalse(query.exists())
        data = self._make_assign_worker_task_request(
            worker.id, -1, success=False)
        self.assertTrue('error' in data['errors'])
        self.assertFalse(query.exists())

        # Worker0 is not a reviewer so this should fail
        task = self.tasks['review_task']
        data = self._make_assign_worker_task_request(
            worker.id, task.id, success=False)
        self.assertTrue('worker_certification_error' in data['errors'])
        self.assertFalse(query.exists())

        # Can't assign to aborted task
        task = self.tasks['aborted']
        data = self._make_assign_worker_task_request(
            worker.id, task.id, success=False)
        self.assertTrue('task_assignment_error' in data['errors'])
        self.assertFalse(query.exists())

    @patch('orchestra.project_api.views.message_experts_slack_group')
    def test_message_project_team(self, mock_message_slack_group):
        project = ProjectFactory(slack_group_id='test-project-1')
        url = '/orchestra/api/project/message_project_team/'
        test_message = 'this is a test message'
        response = self.api_client.post(
            url,
            {'message': test_message, 'project_id': project.id},
            format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(mock_message_slack_group.called)
        # No project id provided
        response = self.api_client.post(
            url, {'message': test_message}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()['message'],
            ('An object with `message` and `project_id` attributes'
             ' should be supplied'))
        # No message provided
        response = self.api_client.post(
            url, {'project_id': project.id}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()['message'],
            ('An object with `message` and `project_id` attributes'
             ' should be supplied'))
        # Non-existent project_id provided
        response = self.api_client.post(
            url, {'message': 'text', 'project_id': 123456}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['message'],
                         'No project for given id')

    def test_permissions(self):
        self.api_client.force_authenticate(user=AnonymousUser())

        response = self.api_client.post(
            '/orchestra/api/project/project_information/',
            {'project_id': 1},
            format='json')
        self.assertEqual(response.status_code, 403)
        returned = load_encoded_json(response.content)
        self.assertEqual(
            returned,
            {'detail': 'You do not have permission to perform this action.'})

    def _delete_keys(self, obj):
        unimportant_keys = (
            'id',
            'task',
            'short_description',
            'start_datetime',
            'end_datetime'
        )
        if isinstance(obj, list):
            for item in obj:
                self._delete_keys(item)

        elif isinstance(obj, dict):
            for key in unimportant_keys:
                try:
                    del obj[key]
                except KeyError:
                    pass
            for value in obj.values():
                self._delete_keys(value)


@override_settings(ORCHESTRA_PROJECT_API_CREDENTIALS={'a': 'b'})
class ProjectAPIAuthTestCase(OrchestraTestCase):

    def setUp(self):
        super().setUp()
        setup_models(self)
        self.authentication = OrchestraProjectAPIAuthentication()

    def test_auth_success(self):
        self.assertEqual(
            self.authentication.fetch_user_data('a'),
            (SignedUser(), 'b'))

    def test_no_key(self):
        with self.assertRaises(AuthenticationFailed):
            self.authentication.fetch_user_data('c')

    def test_misconfigured_credentials(self):
        tmp_setting = settings.ORCHESTRA_PROJECT_API_CREDENTIALS
        del settings.ORCHESTRA_PROJECT_API_CREDENTIALS
        with self.assertRaises(AuthenticationFailed):
            self.authentication.fetch_user_data('a')
        settings.ORCHESTRA_PROJECT_API_CREDENTIALS = tmp_setting
        self.assertEqual(
            self.authentication.fetch_user_data('a'),
            (SignedUser(), 'b'))


class TestTodoApiViewsetTests(EndpointTestCase):
    def setUp(self):
        super().setUp()
        self.request_client = APIClient(enforce_csrf_checks=True)
        self.request_client.force_authenticate(user=SignedUser())
        setup_models(self)
        self.workflow_version = WorkflowVersionFactory()
        self.step = StepFactory(
            slug='step-slug',
            workflow_version=self.workflow_version)
        self.project = ProjectFactory(
            workflow_version=self.workflow_version)
        self.list_url = reverse('orchestra:api:todo-api-list')
        self.todo = TodoFactory(project=self.project)
        self.todo_with_step = TodoFactory(project=self.project, step=self.step)

    def test_permissions(self):
        data = {
            'title': 'Testing title 1',
            'project': self.project.id,
            'step': self.step.slug
        }
        request_client = APIClient(enforce_csrf_checks=True)
        resp = request_client.post(
            self.list_url, data=json.dumps(data),
            content_type='application/json')
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(
            resp.json()['detail'],
            'Authentication credentials were not provided.')

        # Test if a logged in user cannot access this endpoint
        worker = Worker.objects.get(user__username='test_user_6')
        request_client = APIClient(enforce_csrf_checks=True)
        request_client.login(username=worker.user.username,
                             password='defaultpassword')
        resp = request_client.post(
            self.list_url, data=json.dumps(data),
            content_type='application/json')
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(
            resp.json()['detail'],
            'Authentication credentials were not provided.')

    @patch('orchestra.todos.views.notify_todo_created')
    def test_create(self, mock_notify):
        data = {
            'title': 'Testing create action',
            'project': self.project.id,
            'step': self.step.slug,
            'additional_data': {
                'some_key': 1,
                'other_key': None,
                'some_str': 'test',
                'some_bool': False
            }
        }
        resp = self.request_client.post(
            self.list_url, data=json.dumps(data),
            content_type='application/json')
        self.assertEqual(resp.status_code, 201)
        todos = Todo.objects.filter(
            title__startswith='Testing create action',
            project=self.project,
            step=self.step)
        self.assertEqual(todos.count(), 1)
        self.assertTrue(mock_notify.called)

    def test_bulk_create(self):
        todos = Todo.objects.filter(title__startswith='Testing title ')
        self.assertEqual(len(todos), 0)
        data = [
            {
                'title': 'Testing title {}'.format(x),
                'project': self.project.id,
                'step': self.step.slug,
                'additional_data': {
                    'some_key': 1,
                    'other_key': None,
                    'some_str': 'test',
                    'some_bool': False
                }
            } for x in range(10)
        ]
        resp = self.request_client.post(
            self.list_url, data=json.dumps(data),
            content_type='application/json')
        self.assertEqual(resp.status_code, 201)
        todos = Todo.objects.filter(
            title__startswith='Testing title ',
            project=self.project,
            step=self.step)
        self.assertEqual(len(todos), 10)

    def test_get_single_todo_by_pk(self):
        detail_url = reverse(
            'orchestra:api:todo-api-detail',
            kwargs={'pk': self.todo.id})
        resp = self.request_client.get(detail_url)
        self.assertEqual(resp.status_code, 200)

    def test_get_list_of_todos_with_filters_project_id(self):
        url_with_project_filter = '{}?project__id={}'.format(
            self.list_url, self.project.id)
        resp = self.request_client.get(url_with_project_filter)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 2)

    def test_get_list_of_todos_with_filters_step_slug(self):
        url_with_step_filter = '{}?step__slug={}'.format(
            self.list_url, self.todo_with_step.step.slug)
        resp = self.request_client.get(url_with_step_filter)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)
        self.assertEqual(resp.json()[0]['step'], self.todo_with_step.step.slug)

    def test_get_list_of_todos_with_filters_project_id_and_step_slug(self):
        url_with_filters = '{}?project__id={}&step__slug={}'.format(
            self.list_url, self.project.id, self.todo_with_step.step.slug)
        resp = self.request_client.get(url_with_filters)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()[0]['step'], self.todo_with_step.step.slug)

    def test_get_list_of_todos_with_filters_todo_ids(self):
        # Filter by existing todo ids
        ids_to_filter_by = [self.todo.id, self.todo_with_step.id]
        url_with_filters = '{}?&q={}'.format(
            self.list_url,
            json.dumps({'id__in': ids_to_filter_by}))
        resp = self.request_client.get(url_with_filters)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 2)
        for todo in resp.json():
            self.assertTrue(todo['id'] in ids_to_filter_by)

        # Filter by non-existent id
        ids_to_filter_by = [112233445589]
        url_with_filters = '{}?&q={}'.format(
            self.list_url,
            json.dumps({'id__in': ids_to_filter_by}))
        resp = self.request_client.get(url_with_filters)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 0)

    @patch('orchestra.todos.views.notify_single_todo_update')
    def test_update_functionality(self, mock_notify):
        todo1 = TodoFactory(
            project=self.project, step=self.step, title='Test title1')
        todo2 = TodoFactory(
            project=self.project, step=self.step, title='Test title2')
        # Set title of the todo2 to todo1
        serialized = BulkTodoSerializer(todo2).data
        detail_url = reverse(
            'orchestra:api:todo-api-detail',
            kwargs={'pk': todo1.id})
        resp = self.request_client.put(
            detail_url,
            data=json.dumps(serialized),
            content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        # Check if title is updated
        updated_todo_1 = Todo.objects.get(pk=todo1.pk)
        self.assertEqual(updated_todo_1.title, todo2.title)

    @patch('orchestra.todos.views.notify_single_todo_update')
    def test_partial_update_functionality(self, mock_notify):
        detail_url = reverse(
            'orchestra:api:todo-api-detail',
            kwargs={'pk': self.todo.id})
        expected_title = 'Partial update title'
        resp = self.request_client.patch(
            detail_url,
            data=json.dumps({
                'title': expected_title,
                'step': self.step.slug,
                'project': self.project.id
            }),
            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['title'], expected_title)
        self.assertEqual(resp.json()['step'], self.step.slug)
        self.assertEqual(resp.json()['project'], self.project.id)

        resp = self.request_client.patch(
            detail_url,
            data=json.dumps({
                'title': expected_title,
                'step': self.step.id,
            }),
            content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.json()['project'],
            ['if step is given, project should also be supplied.'])

    def test_destroy_functionality(self):
        all_todos_count = Todo.objects.count()
        self.assertEqual(all_todos_count, 2)
        detail_url = reverse(
            'orchestra:api:todo-api-detail',
            kwargs={'pk': self.todo.id})
        resp = self.request_client.delete(detail_url)
        self.assertEqual(resp.status_code, 204)
        all_todos_count = Todo.objects.count()
        self.assertEqual(all_todos_count, 1)

        marked_as_deleted = Todo.unsafe_objects.get(pk=self.todo.pk)
        self.assertTrue(marked_as_deleted.is_deleted)
        self.assertEqual(marked_as_deleted, self.todo)

    def test_bulk_update(self):
        todo1 = TodoFactory(
            project=self.project, step=self.step, title='Test title1')
        todo2 = TodoFactory(
            project=self.project, step=self.step, title='Test title2')
        todo3 = TodoFactory(
            project=self.project, step=self.step, title='Test title3')
        todo_wo_project = TodoFactory(
            title='Test title3')
        todo_should_not_be_updated = TodoFactory(
            project=self.project, step=self.step, title='Not updated')
        serialized = BulkTodoSerializer([todo3, todo2, todo1], many=True).data
        # Change titles
        updated = [
            self._change_attr(x, 'title',  'updated title {}'.format(x['id']))
            for x in serialized]
        resp = self.request_client.put(
            self.list_url, data=json.dumps(updated),
            content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        updated_todos = Todo.objects.filter(
            id__in=[todo1.id, todo2.id, todo3.id])
        for todo in updated_todos:
            self.assertEqual(todo.title, 'updated title {}'.format(todo.id))
        self.assertEqual(todo_should_not_be_updated.title, 'Not updated')

        serialized = BulkTodoSerializer([todo_wo_project], many=True).data
        updated = [
            self._change_attr(x, 'title',  'updated title {}'.format(x['id']))
            for x in serialized]
        resp = self.request_client.put(
            self.list_url, data=json.dumps(updated),
            content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()[0]['step'],
                         ['This field may not be null.'])

    def test_bulk_partial_update(self):
        todo1 = TodoFactory(
            project=self.project, step=self.step, title='Test title1')
        todo2 = TodoFactory(
            project=self.project, step=self.step, title='Test title2')
        todo3 = TodoFactory(
            project=self.project, step=self.step, title='Test title3')
        todo_should_not_be_updated = TodoFactory(
            project=self.project, step=self.step, title='Not updated')
        # Change titles
        todos_with_updated_titles = [{
            'id': x.id,
            'title': 'Updated title {}'.format(x.id),
            'step': x.step.slug,
            'project': x.project.id
        } for x in [todo1, todo3, todo2]]
        resp = self.request_client.patch(
            self.list_url, data=json.dumps(todos_with_updated_titles),
            content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        updated_todos = Todo.objects.filter(
            id__in=[todo1.id, todo2.id, todo3.id])
        for todo in updated_todos:
            self.assertEqual(todo.title, 'Updated title {}'.format(todo.id))
        self.assertEqual(todo_should_not_be_updated.title, 'Not updated')

    def _change_attr(self, item, attr, value):
        item[attr] = value
        return item
