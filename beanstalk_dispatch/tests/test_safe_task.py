import time

from beanstalk_dispatch.safe_task import SafeTask
from datetime import timedelta
from django.test import TestCase
from unittest.mock import MagicMock


def get_mock_task():
    MockSafeTask = SafeTask
    MockSafeTask.run = MagicMock()
    MockSafeTask.on_error = MagicMock()
    MockSafeTask.on_success = MagicMock()
    MockSafeTask.on_completion = MagicMock()
    return MockSafeTask()


def _sleep_too_long():
    time.sleep(10)
    return MagicMock()


class SafeTaskTestCase(TestCase):

    test_error = Exception('Test exception')
    test_args = ['test', 'args']
    test_kwargs = {'test': 'kwargs'}

    """
    Test the basic SafeTask functionality
    """

    def test_task_success(self):
        """
        Test error free task processing
        """
        task = get_mock_task()
        task.process()

        task.run.assert_called_once_with()
        task.on_success.assert_called_once_with()
        task.on_error.assert_not_called()
        task.on_completion.assert_called_once_with()

    def test_task_success_args_kwargs(self):
        task = get_mock_task()
        task.process(*self.test_args, **self.test_kwargs)

        task.run.assert_called_once_with(*self.test_args, **self.test_kwargs)
        task.on_success.assert_called_once_with(
            *self.test_args, **self.test_kwargs)
        task.on_error.assert_not_called()
        task.on_completion.assert_called_once_with(
            *self.test_args, **self.test_kwargs)

    def test_task_error(self):
        """
        Test running a task that fails
        """
        task = get_mock_task()
        task.run.side_effect = self.test_error
        task.process()

        task.run.assert_called_once_with()
        task.on_success.assert_not_called()
        task.on_error.assert_called_once_with(self.test_error)
        task.on_completion.assert_called_once_with()

    def test_task_error_args_kwargs(self):
        task = get_mock_task()
        task.run.side_effect = self.test_error
        task.process(*self.test_args, **self.test_kwargs)

        task.run.assert_called_once_with(*self.test_args, **self.test_kwargs)
        task.on_success.assert_not_called()
        task.on_error.assert_called_once_with(
            self.test_error, *self.test_args, **self.test_kwargs)
        task.on_completion.assert_called_once_with(
            *self.test_args, **self.test_kwargs)

    def test_task_error_timeout(self):
        # Test timeout
        task = get_mock_task()
        task.timeout_timedelta = timedelta(seconds=0.1)
        task.run = MagicMock(side_effect=_sleep_too_long)
        task.process()

        task.run.assert_called_once_with()
        task.on_success.assert_not_called()
        # There is a problem with mocks when asserting the Exception type when
        # it is TimeoutError
        self.assertEqual(task.on_error.call_count, 1)
        self.assertEqual(str(task.on_error.call_args), 'call(TimeoutError())')
        task.on_completion.assert_called_once_with()
