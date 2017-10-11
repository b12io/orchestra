from unittest.mock import patch

from django.test.utils import override_settings

from orchestra.tests.helpers import OrchestraTestCase
from orchestra.utils.machine_step_scheduler import \
    AsynchronousMachineStepScheduler
from orchestra.utils.machine_step_scheduler import MachineStepScheduler


class MachineStepSchedulerTestCase(OrchestraTestCase):

    def setUp(self):
        super().setUp()

    def test_machine_step_schedule(self):
        scheduler = MachineStepScheduler()
        with self.assertRaises(NotImplementedError):
            scheduler.schedule(1, '')

    @patch('orchestra.utils.machine_step_scheduler.SynchronousMachineStepScheduler.schedule')  # noqa
    def test_asynchronous_scheduler(self, mock_schedule):
        scheduler = AsynchronousMachineStepScheduler()
        scheduler.schedule(1, 'step1')
        mock_schedule.assert_called_once_with(1, 'step1')

    @patch('orchestra.utils.machine_step_scheduler.schedule_function')
    @override_settings(PRODUCTION=True, WORK_QUEUE=None)
    def test_asynchronous_scheduler_prod(self, mock_schedule):
        scheduler = AsynchronousMachineStepScheduler()
        scheduler.schedule(1, 'step1')
        mock_schedule.assert_called_once_with(None, 'machine_task_executor', 1,
                                              'step1')
