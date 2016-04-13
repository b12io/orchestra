import datetime
import json

from unittest.mock import patch

from django.core.urlresolvers import reverse
from django.test import Client as RequestClient
from django.utils import timezone
from rest_framework import serializers

from orchestra.core.errors import TaskStatusError
from orchestra.core.errors import TimerError
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.models import TaskTimer
from orchestra.models import TimeEntry
from orchestra.models import Worker
from orchestra.project_api.serializers import TaskTimerSerializer
from orchestra.project_api.serializers import TimeEntrySerializer
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.tests.helpers.fixtures import UserFactory
from orchestra.tests.helpers.fixtures import WorkerFactory


class EndpointTests(OrchestraTestCase):

    def _verify_bad_request(self, response, message):
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content.decode())
        self.assertEqual(data['message'], message)
        self.assertEqual(data['error'], 400)


class TimeEntriesViewTestCase(EndpointTests):

    def setUp(self):
        super().setUp()
        setup_models(self)
        self.request_client = RequestClient()
        self.worker = Worker.objects.get(user__username='test_user_6')
        self.request_client.login(username=self.worker.user.username,
                                  password='defaultpassword')
        self.url = reverse('orchestra:orchestra:time_entries')
        self.tasks = Task.objects.filter(assignments__worker=self.worker)
        self.task = self.tasks[0]
        self.assignment = (self.task.assignments.filter(worker=self.worker)
                           .first())
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

    def _verify_time_entries(self, data):
        for time_entry in data:
            serializer = TimeEntrySerializer(data=time_entry)
            self.assertTrue(serializer.is_valid())
            self.assertEqual(time_entry['worker'], self.worker.id)

    def test_time_entries_get(self):
        resp = self.request_client.get(self.url)
        data = json.loads(resp.content.decode())
        self.assertEqual(len(data), self.tasks.count())
        self._verify_time_entries(data)

    @patch('orchestra.views.time_entries_for_worker')
    def test_time_entries_get_task_id(self, mock_func):
        mock_func.return_value = [self.time_entry_data]
        self.request_client.get(self.url,
                                data={'task-id': self.task.id})
        mock_func.assert_called_with(self.worker,
                                     task_id=str(self.task.id))

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


class TimerEndpointTests(EndpointTests):

    def setUp(self):
        super().setUp()
        user = UserFactory(username='test_user')
        self.worker = WorkerFactory(user=user)
        self.request_client = RequestClient()
        self.request_client.login(username=self.worker.user.username,
                                  password='defaultpassword')
        self.time = timezone.now()

    @patch('orchestra.views.time_tracking.start_timer')
    def test_start_timer(self, mock_start):
        timer = TaskTimer(worker=self.worker, start_time=self.time)
        timer.save()
        mock_start.return_value = timer
        resp = self.request_client.post(
            reverse('orchestra:orchestra:start_timer'),
            data=json.dumps({'assignment': '11'}),
            content_type='application/json')
        mock_start.assert_called_with(self.worker, assignment_id='11')
        data = json.loads(resp.content.decode())
        serializer = TaskTimerSerializer(timer)
        self.assertEqual(data, serializer.data)

    @patch('orchestra.views.time_tracking.start_timer',
           side_effect=TaskAssignment.DoesNotExist)
    def test_start_timer_worker_not_assigned(self, mock_start):
        resp = self.request_client.post(
            reverse('orchestra:orchestra:start_timer'),
            data=json.dumps({'assignment': '11'}),
            content_type='application/json')
        self._verify_bad_request(resp,
                                 'Worker is not assigned to this task id.')

    @patch('orchestra.views.time_tracking.start_timer',
           side_effect=TimerError('test'))
    def test_start_timer_timer_already_running(self, mock_start):
        resp = self.request_client.post(
            reverse('orchestra:orchestra:start_timer'),
            data=json.dumps({'assignment': '11'}),
            content_type='application/json')
        self._verify_bad_request(resp, 'test')

    @patch('orchestra.views.time_tracking.stop_timer')
    def test_stop_timer(self, mock_stop):
        time_entry = TimeEntry(worker=self.worker, date=self.time.date(),
                               time_worked=datetime.timedelta(hours=1))
        time_entry.save()
        mock_stop.return_value = time_entry
        resp = self.request_client.post(
            reverse('orchestra:orchestra:stop_timer'),
            data=json.dumps({}),
            content_type='application/json')
        mock_stop.assert_called_with(self.worker)
        data = json.loads(resp.content.decode())
        serializer = TimeEntrySerializer(time_entry)
        self.assertEqual(data, serializer.data)

    @patch('orchestra.views.time_tracking.stop_timer',
           side_effect=TimerError('test'))
    def test_stop_timer_timer_not_running(self, mock_stop):
        resp = self.request_client.post(
            reverse('orchestra:orchestra:stop_timer'),
            data=json.dumps({}),
            content_type='application/json')
        self._verify_bad_request(resp, 'test')

    @patch('orchestra.views.time_tracking.get_timer_current_duration',
           return_value=datetime.timedelta(hours=1))
    def test_get_timer(self, mock_get):
        resp = self.request_client.get(
            reverse('orchestra:orchestra:get_timer'))
        mock_get.assert_called_with(self.worker)
        data = json.loads(resp.content.decode())
        self.assertEqual(data, '1:00:00')
