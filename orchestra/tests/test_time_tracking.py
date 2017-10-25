import datetime
from unittest.mock import patch

from django.utils import timezone

from orchestra.core.errors import TimerError
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.models import TaskTimer
from orchestra.models import TimeEntry
from orchestra.models import Worker
from orchestra.tests.helpers import OrchestraTransactionTestCase
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.utils.time_tracking import get_timer_current_duration
from orchestra.utils.time_tracking import get_timer_object
from orchestra.utils.time_tracking import start_timer
from orchestra.utils.time_tracking import stop_timer


class TaskTimerTests(OrchestraTransactionTestCase):

    def setUp(self):
        super().setUp()
        setup_models(self)
        self.worker = Worker.objects.get(user__username='test_user_6')
        self.tasks = Task.objects.filter(assignments__worker=self.worker)
        self.task = self.tasks[0]
        self.assignment = (self.task.assignments.filter(worker=self.worker)
                           .first())
        self.time_entry_data = {'date': '2016-05-01',
                                'time_worked': '00:30:00',
                                'description': 'test description'}
        self.time = timezone.now()

        def fake_now():
            """ Patch timezone.now so we can test timer. """
            return self.time

        patcher = patch('orchestra.utils.time_tracking.timezone.now', fake_now)
        self.addCleanup(patcher.stop)
        patcher.start()

    def test_get_timer_object_created(self):
        with self.assertRaises(TaskTimer.DoesNotExist):
            self.worker.timer
        timer = get_timer_object(self.worker)
        self.assertEqual(timer, self.worker.timer)

    def test_get_timer_object_not_created(self):
        timer = TaskTimer(worker=self.worker)
        timer.save()
        new_timer = get_timer_object(self.worker)

        # Function should return the already created timer object.
        self.assertEqual(new_timer, timer)

    def test_start_timer(self):
        start_timer(self.worker)
        timer = self.worker.timer
        self.assertEqual(timer.start_time, self.time)

    def test_start_timer_already_running(self):
        timer = TaskTimer(worker=self.worker,
                          start_time=self.time)
        timer.save()
        with self.assertRaisesRegex(TimerError, 'Timer has already started'):
            start_timer(self.worker)

    def test_start_timer_with_assignment(self):
        start_timer(self.worker, assignment_id=self.assignment.id)
        timer = self.worker.timer
        self.assertEqual(timer.assignment, self.assignment)

    def test_start_timer_worker_not_assigned(self):
        # Find task assignment that worker is not assigned to.
        assignment = (TaskAssignment.objects.exclude(worker=self.worker)
                      .first())
        with self.assertRaises(TaskAssignment.DoesNotExist):
            start_timer(self.worker, assignment_id=assignment.id)

    def test_stop_timer(self):
        timer = TaskTimer(worker=self.worker,
                          assignment=self.assignment,
                          start_time=self.time)
        timer.save()
        start_time = self.time
        self.time = self.time + datetime.timedelta(hours=1)
        time_entry = stop_timer(self.worker)

        # Time entry object is created correctly.
        self.assertEqual(time_entry.worker, self.worker)
        self.assertEqual(time_entry.date, start_time.date())
        self.assertEqual(time_entry.time_worked, datetime.timedelta(hours=1))
        self.assertEqual(time_entry.assignment, self.assignment)
        self.assertEqual(time_entry.timer_start_time, start_time)
        self.assertEqual(time_entry.timer_stop_time, self.time)

        # Timer object should be reset.
        timer.refresh_from_db()
        self.assertIsNone(timer.start_time)
        self.assertIsNone(timer.stop_time)

    def test_stop_timer_not_running(self):
        timer = TaskTimer(worker=self.worker)
        timer.save()
        with self.assertRaisesRegex(TimerError, 'Timer not started'):
            stop_timer(self.worker)

    @patch('orchestra.utils.time_tracking._reset_timer', side_effect=Exception)
    def test_stop_timer_atomic(self, mock_reset):
        timer = TaskTimer(worker=self.worker, start_time=self.time)
        timer.save()
        time_entries_count = TimeEntry.objects.count()
        self.assertIsNone(timer.stop_time)

        with self.assertRaises(Exception):
            stop_timer(self.worker)

        # Verify that transaction rolled back.
        timer.refresh_from_db()
        self.assertIsNone(timer.stop_time)
        self.assertEqual(TimeEntry.objects.count(), time_entries_count)

    def test_get_timer_current_duration(self):
        timer = TaskTimer(worker=self.worker,
                          assignment=self.assignment,
                          start_time=self.time)
        timer.save()
        self.time = self.time + datetime.timedelta(hours=1)
        duration = get_timer_current_duration(self.worker)
        self.assertEqual(duration, datetime.timedelta(hours=1))

    def test_get_timer_current_duration_no_start_time(self):
        timer = TaskTimer(worker=self.worker,
                          assignment=self.assignment)
        timer.save()
        duration = get_timer_current_duration(self.worker)
        self.assertIsNone(duration)
