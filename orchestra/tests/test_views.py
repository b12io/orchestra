import datetime
import json

from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware

from orchestra.core.errors import TimerError
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.models import TaskTimer
from orchestra.models import TimeEntry
from orchestra.models import Worker
from orchestra.project_api.serializers import TaskTimerSerializer
from orchestra.project_api.serializers import TimeEntrySerializer
from orchestra.tests.helpers import EndpointTestCase
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import UserFactory
from orchestra.tests.helpers.fixtures import WorkerFactory
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.utils.load_json import load_encoded_json
from orchestra.views import bad_request
from orchestra.views import forbidden
from orchestra.views import internal_server_error
from orchestra.views import not_found


class TimeEntriesEndpointTests(EndpointTestCase):

    def setUp(self):
        super().setUp()
        setup_models(self)
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

    def test_time_entries_get(self):
        resp = self.request_client.get(self.url)
        data = load_encoded_json(resp.content)
        self.assertEqual(len(data), self.tasks.count())
        self._verify_time_entries(data)

    def test_time_entries_get_assignment_id(self):
        resp = self.request_client.get(self.url,
                                       data={'assignment': self.assignment.id})
        data = load_encoded_json(resp.content)
        self.assertEqual(len(data), 1)
        self._verify_time_entries(data)

    def test_time_entries_assignment_missing(self):
        resp = self.request_client.get(self.url, data={'assignment': '111'})
        data = load_encoded_json(resp.content)
        self.assertEqual(len(data), 0)

    def test_time_entries_post(self):
        resp = self.request_client.post(self.url,
                                        data=json.dumps(self.time_entry_data),
                                        content_type='application/json')
        data = load_encoded_json(resp.content)
        time_entry = TimeEntry.objects.get(id=data['id'])
        self.assertEqual(time_entry.worker, self.worker)
        self.assertIsNone(time_entry.assignment)
        self.assertIsNone(time_entry.timer_start_time)
        self.assertIsNone(time_entry.timer_stop_time)
        self.assertFalse(time_entry.is_deleted)
        self.assertEqual(time_entry.description, 'test description')
        self.assertEqual(time_entry.date, datetime.date(2016, 5, 1))
        self.assertEqual(time_entry.time_worked,
                         datetime.timedelta(minutes=30))

    def test_time_entries_post_invalid_data(self):
        self.time_entry_data['date'] = 'hi'  # Invalid date.
        resp = self.request_client.post(self.url,
                                        data=json.dumps(self.time_entry_data),
                                        content_type='application/json')
        self.assertEqual(resp.status_code, 400)

    def test_time_entries_post_cannot_set_worker(self):
        """
        Worker is a read-only field and writes to it will be ignored by the
        serializer.
        """
        worker = Worker.objects.exclude(id=self.worker.id).first()
        self.time_entry_data['worker'] = worker.id
        resp = self.request_client.post(self.url,
                                        data=json.dumps(self.time_entry_data),
                                        content_type='application/json')
        data = load_encoded_json(resp.content)
        time_entry = TimeEntry.objects.get(id=data['id'])
        self.assertNotEqual(time_entry.worker, worker)
        self.assertEqual(time_entry.worker, self.worker)

    def test_time_entry_delete(self):
        """
        Delete should mark instance as deleted, not delete instance.
        """
        time_entry = TimeEntry.objects.filter(worker=self.worker).first()
        self.request_client.delete(
            reverse('orchestra:orchestra:time_entry',
                    kwargs={'pk': time_entry.id}))
        self.assertFalse(TimeEntry.objects.filter(id=time_entry.id).exists())

    def test_time_entry_update(self):
        time_entry = TimeEntry.objects.filter(worker=self.worker).first()
        serializer = TimeEntrySerializer(time_entry)
        data = serializer.data
        data['time_worked'] = '10:00:00'  # Update time worked.
        self.request_client.put(
            reverse('orchestra:orchestra:time_entry',
                    kwargs={'pk': time_entry.id}),
            data=json.dumps(data),
            content_type='application/json')
        time_entry.refresh_from_db()
        self.assertEqual(time_entry.time_worked, datetime.timedelta(hours=10))

    def test_time_entry_update_invalid_data(self):
        time_entry = TimeEntry.objects.filter(worker=self.worker).first()
        serializer = TimeEntrySerializer(time_entry)
        data = serializer.data
        data['date'] = '2'  # Invalid date.
        resp = self.request_client.put(
            reverse('orchestra:orchestra:time_entry',
                    kwargs={'pk': time_entry.id}),
            data=json.dumps(data),
            content_type='application/json')
        self.assertEqual(resp.status_code, 400)


class TimerEndpointTests(EndpointTestCase):

    def setUp(self):
        super().setUp()
        user = UserFactory(username='test_user')
        self.worker = WorkerFactory(user=user)
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
        data = load_encoded_json(resp.content)
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
    def test_start_timer_timer_error(self, mock_start):
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
        data = load_encoded_json(resp.content)
        serializer = TimeEntrySerializer(time_entry)
        self.assertEqual(data, serializer.data)

    @patch('orchestra.views.time_tracking.stop_timer',
           side_effect=TimerError('test'))
    def test_stop_timer_timer_error(self, mock_stop):
        resp = self.request_client.post(
            reverse('orchestra:orchestra:stop_timer'),
            data=json.dumps({}),
            content_type='application/json')
        self._verify_bad_request(resp, 'test')

    @patch('orchestra.views.time_tracking.get_timer_current_duration',
           return_value=datetime.timedelta(hours=1))
    def test_get_timer(self, mock_get):
        timer = TaskTimer(
            worker=self.worker,
            start_time=timezone.now())
        timer.save()
        resp = self.request_client.get(
            reverse('orchestra:orchestra:get_timer'))
        mock_get.assert_called_with(self.worker)
        data = load_encoded_json(resp.content)
        expected = TaskTimerSerializer(timer).data
        expected['time_worked'] = '1:00:00'
        self.assertEqual(data, expected)


class TestErrorViews(OrchestraTestCase):

    def assert_error_view(self, handler, status_code, exception=None):
        request = RequestFactory().get('/')
        middleware = SessionMiddleware()
        middleware.process_request(request)
        request.session.save()

        if exception:
            response = handler(request, exception)
        else:
            response = handler(request)
        self.assertEqual(response.status_code, status_code)

    def test_bad_request(self):
        self.assert_error_view(bad_request, 400, exception=Exception())

    def test_forbidden(self):
        self.assert_error_view(forbidden, 403, exception=Exception())

    def test_not_found(self):
        self.assert_error_view(not_found, 404, exception=Exception())

    def test_internal_server_error(self):
        self.assert_error_view(internal_server_error, 500)
