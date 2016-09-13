import time

from beanstalk_dispatch.safe_task import SafeTask
from django.test import TestCase
from unittest.mock import MagicMock


def get_mock_task(*args, **kwargs):
    MockSafeTask = SafeTask
    MockSafeTask.run = MagicMock()
    MockSafeTask.on_error = MagicMock()
    MockSafeTask.on_success = MagicMock()
    MockSafeTask.reschedule = MagicMock()
    MockSafeTask.on_completion = MagicMock()
    return MockSafeTask(*args, **kwargs)


def _sleep_too_long():
    time.sleep(10)
    return MagicMock()


class SafeTaskTestCase(TestCase):

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
        task.reschedule.assert_not_called()
        task.on_error.assert_not_called()
        task.on_completion.assert_called_once_with()

        # Test args/kwargs
        test_args = ['test', 'args']
        test_kwargs = {'test': 'kwargs'}
        task = get_mock_task(task_args=test_args, task_kwargs=test_kwargs)
        task.process()

        task.run.assert_called_once_with(*test_args, **test_kwargs)
        task.on_success.assert_called_once_with()
        task.reschedule.assert_not_called()
        task.on_error.assert_not_called()
        task.on_completion.assert_called_once_with()

        # Test retry on error, since there is no error, there should be no
        # retry
        task = get_mock_task(num_retries=5)
        task.process()

        task.run.assert_called_once_with()
        task.on_success.assert_called_once_with()
        task.reschedule.assert_not_called()
        task.on_error.assert_not_called()
        task.on_completion.assert_called_once_with()

        # Test passing in a runnable
        test_runnable = MagicMock()
        task = get_mock_task(runnable=test_runnable)
        task.process()

        test_runnable.assert_called_once_with()
        task.run.assert_called_once_with()
        task.on_success.assert_called_once_with()
        task.reschedule.assert_not_called()
        task.on_error.assert_not_called()
        task.on_completion.assert_called_once_with()

    def test_task_error(self):
        """
        Test running a task that fails
        """
        test_error = Exception('Test exception')
        task = get_mock_task()
        task.run.side_effect = test_error
        task.process()

        task.run.assert_called_once_with()
        task.on_success.assert_not_called()
        task.reschedule.assert_not_called()
        task.on_error.assert_called_once_with(test_error)
        task.on_completion.assert_called_once_with()

        # Test args/kwargs
        test_args = ['test', 'args']
        test_kwargs = {'test': 'kwargs'}
        task = get_mock_task(task_args=test_args, task_kwargs=test_kwargs)
        task.run.side_effect = test_error
        task.process()

        task.run.assert_called_once_with(*test_args, **test_kwargs)
        task.on_success.assert_not_called()
        task.reschedule.assert_not_called()
        task.on_error.assert_called_once_with(test_error)
        task.on_completion.assert_called_once_with()

        # Test retry on error
        test_args = ['test', 'args']
        test_kwargs = {'test': 'kwargs'}
        task = get_mock_task(
            num_retries=5, task_args=test_args, task_kwargs=test_kwargs)
        task.run.side_effect = test_error
        task.process()

        task.run.assert_called_once_with(*test_args, **test_kwargs)
        task.on_success.assert_not_called()
        task.reschedule.assert_called_once_with()
        task.on_error.assert_called_once_with(test_error)
        task.on_completion.assert_called_once_with()

        # Test timeout
        test_runnable = MagicMock(side_effect=_sleep_too_long)
        task = get_mock_task(runnable=test_runnable, timeout_seconds=0.1)
        task.process()

        task.run.assert_called_once_with()
        task.on_success.assert_not_called()
        task.reschedule.assert_not_called()
        # There is a problem with mocks when asserting the Exception type when
        # it is TimeoutError
        self.assertEqual(task.on_error.call_count, 1)
        self.assertEqual(str(task.on_error.call_args), 'call(TimeoutError())')
        task.on_completion.assert_called_once_with()
