import json

from unittest.mock import patch

from django.core.urlresolvers import reverse
from django.test import Client as RequestClient
from django.test import RequestFactory
from rest_framework import serializers

from orchestra.core.errors import TaskStatusError
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.models import Worker
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import setup_models


class TimeEntriesViewTestCase(OrchestraTestCase):

    def setUp(self):
        super().setUp()
        setup_models(self)
        self.request_client = RequestClient()
        self.factory = RequestFactory()
        self.worker = Worker.objects.get(user__username='test_user_6')
        self.request_client.login(username=self.worker.user.username,
                                  password='defaultpassword')
        self.url = reverse('orchestra:orchestra:time_entries')
        self.tasks = Task.objects.filter(assignments__worker=self.worker)
        self.time_entry_data = {'date': '2016-05-01',
                                'time_worked': '00:30:00',
                                'description': 'test description'}

    def _verify_missing_task(self, response):
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content.decode())
        self.assertEqual(data['message'], 'No task for given id')
        self.assertEqual(data['error'], 400)

    def _verify_worker_not_assigned(self, response):
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content.decode())
        self.assertEqual(data['message'],
                         'Worker is not assigned to this task id.')
        self.assertEqual(data['error'], 400)

    def _verify_bad_request(self, response, message):
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content.decode())
        self.assertEqual(data['message'], message)
        self.assertEqual(data['error'], 400)

    def test_time_entries_get(self):
        resp = self.request_client.get(self.url)
        data = json.loads(resp.content.decode())
        self.assertEqual(len(data), self.tasks.count())

    @patch('orchestra.views.time_entries_for_worker')
    def test_time_entries_get_task_id(self, mock_func):
        mock_func.return_value = [self.time_entry_data]
        self.request_client.get(self.url,
                                data={'task-id': self.tasks[0].id})
        mock_func.assert_called_with(self.worker,
                                     task_id=str(self.tasks[0].id))

    @patch('orchestra.views.time_entries_for_worker',
           side_effect=Task.DoesNotExist)
    def test_time_entries_get_task_missing(self, mock_func):
        resp = self.request_client.get(self.url)
        self._verify_missing_task(resp)

    @patch('orchestra.views.time_entries_for_worker',
           side_effect=TaskAssignment.DoesNotExist)
    def test_time_entries_get_worker_not_assigned(self, mock_func):
        resp = self.request_client.get(self.url)
        self._verify_worker_not_assigned(resp)

    @patch('orchestra.views.save_time_entry')
    def test_time_entries_post(self, mock_func):
        mock_func.return_value = self.time_entry_data

        # Set task id in request body.
        self.time_entry_data['task_id'] = self.tasks[0].id
        self.request_client.post(self.url,
                                 data=json.dumps(self.time_entry_data),
                                 content_type='application/json')

        # Remove task_id from dictionary so we can compare with mock_func
        # call.
        self.time_entry_data.pop('task_id')
        mock_func.assert_called_with(self.worker, self.tasks[0].id,
                                     self.time_entry_data)

    @patch('orchestra.views.save_time_entry', side_effect=Task.DoesNotExist)
    def test_time_entries_post_task_missing(self, mock_func):
        # Set task id in request body.
        self.time_entry_data['task_id'] = self.tasks[0].id
        resp = self.request_client.post(self.url,
                                        data=json.dumps(self.time_entry_data),
                                        content_type='application/json')
        self._verify_missing_task(resp)

    @patch('orchestra.views.save_time_entry',
           side_effect=TaskAssignment.DoesNotExist)
    def test_time_entries_post_worker_not_assigned(self, mock_func):
        # Set task id in request body.
        self.time_entry_data['task_id'] = self.tasks[0].id
        resp = self.request_client.post(self.url,
                                        data=json.dumps(self.time_entry_data),
                                        content_type='application/json')
        self._verify_worker_not_assigned(resp)

    @patch('orchestra.views.logger')
    @patch('orchestra.views.save_time_entry',
           side_effect=TaskStatusError('Error'))
    def test_time_entries_post_task_complete(self, mock_func, mock_logger):
        # Set task id in request body.
        self.time_entry_data['task_id'] = self.tasks[0].id
        resp = self.request_client.post(self.url,
                                        data=json.dumps(self.time_entry_data),
                                        content_type='application/json')
        self._verify_bad_request(resp, 'Error')

    @patch('orchestra.views.logger')
    @patch('orchestra.views.save_time_entry',
           side_effect=serializers.ValidationError('Error'))
    def test_time_entries_post_data_invalid(self, mock_func, mock_logger):
        # Set task id in request body.
        self.time_entry_data['task_id'] = self.tasks[0].id
        resp = self.request_client.post(self.url,
                                        data=json.dumps(self.time_entry_data),
                                        content_type='application/json')
        self._verify_bad_request(resp, "['Error']")
