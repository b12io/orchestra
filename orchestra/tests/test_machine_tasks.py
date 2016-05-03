from unittest.mock import patch

from orchestra.core.errors import MachineExecutionError
from orchestra.machine_tasks import execute
from orchestra.models import Iteration
from orchestra.models import Project
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.tests.helpers.fixtures import ProjectFactory
from orchestra.utils.task_lifecycle import create_subsequent_tasks


class MachineTaskTestCase(OrchestraTestCase):
    def setUp(self):
        super().setUp()
        setup_models(self)

        machine_workflow_version = (
            self.workflow_versions['machine_workflow_version'])
        self.step = machine_workflow_version.steps.get(slug='machine_step')
        self.assertIsNotNone(self.step)
        self.step.execution_function = {
            'path': 'orchestra.tests.helpers.workflow.machine_task_function',
        }
        self.step.save()
        patcher = patch(
            'orchestra.tests.helpers.workflow.machine_task_function',
            return_value={'data': ''})
        self.machine_function_mock = patcher.start()
        self.addCleanup(patcher.stop)

        self.project = ProjectFactory(
            workflow_version=machine_workflow_version)
        create_subsequent_tasks(self.project)
        self.task = self.project.tasks.first()
        self.assertIsNotNone(self.task)

        # Since create_subsequent_tasks will automatically run the machine task
        # we need to reset the task each time it's called
        self._reset_task()

    def _reset_task(self):
        self.task.status = Task.Status.AWAITING_PROCESSING
        self.task.save()
        self.task.assignments.all().delete()
        self.machine_function_mock.call_count = 0

    def _assert_correct_machine_task_state(
            self, assignment_status, task_status):
        self.task.refresh_from_db()
        assignment = self.task.assignments.first()
        self.assertEquals(assignment.status, assignment_status)
        self.assertEquals(self.task.status, task_status)

        # Check correct iteration state
        self.assertEquals(assignment.iterations.count(), 1)
        iteration = assignment.iterations.first()
        if task_status == Task.Status.COMPLETE:
            expected_status = Iteration.Status.REQUESTED_REVIEW
            expected_data = assignment.in_progress_task_data
            self.assertIsNotNone(iteration.end_datetime)
        else:
            expected_status = Iteration.Status.PROCESSING
            expected_data = {}
            self.assertIsNone(iteration.end_datetime)

        self.assertEquals(iteration.status, expected_status)
        self.assertEquals(iteration.submitted_data, expected_data)

        # Assert that machine function is called once and there is only one
        # assignment regardless of state
        self.assertEquals(self.machine_function_mock.call_count, 1)
        self.assertEquals(self.task.assignments.count(), 1)

    def test_new_task(self):
        self._reset_task()
        execute(self.project.id, self.step.slug)
        self._assert_correct_machine_task_state(
            TaskAssignment.Status.SUBMITTED, Task.Status.COMPLETE)

    def test_already_processing_task(self):
        self._reset_task()
        execute(self.project.id, self.step.slug)

        # Pretend that the task is still processing
        self.task.status = Task.Status.PROCESSING
        self.task.save()
        assignment = self.task.assignments.first()
        assignment.status = TaskAssignment.Status.PROCESSING
        assignment.save()

        # Reset iteration for assignment
        assignment.iterations.all().delete()
        Iteration.objects.create(
            assignment=assignment,
            start_datetime=assignment.start_datetime)

        # Another machine attempts to perform task
        with self.assertRaises(MachineExecutionError):
            execute(self.project.id, self.step.slug)
        self._assert_correct_machine_task_state(
            TaskAssignment.Status.PROCESSING, Task.Status.PROCESSING)

    def test_already_completed_task(self):
        self._reset_task()
        execute(self.project.id, self.step.slug)
        with self.assertRaises(MachineExecutionError):
            execute(self.project.id, self.step.slug)
        self._assert_correct_machine_task_state(
            TaskAssignment.Status.SUBMITTED, Task.Status.COMPLETE)

    @patch('orchestra.machine_tasks.logger')
    def test_marking_failed_task_assignment(self, mock_logger):
        self.machine_function_mock.side_effect = Exception('Function failed.')
        self._reset_task()
        execute(self.project.id, self.step.slug)
        self._assert_correct_machine_task_state(
            TaskAssignment.Status.FAILED, Task.Status.PROCESSING)
        mock_logger.exception.assert_called_with('Machine task has failed')
        self.machine_function_mock.side_effect = None

    def test_reassigning_failed_task_assignment(self):
        self._reset_task()
        execute(self.project.id, self.step.slug)

        # Pretend that the machine task failed
        self.task.status = Task.Status.PROCESSING
        self.task.save()
        assignment = self.task.assignments.first()
        assignment.status = TaskAssignment.Status.FAILED
        assignment.save()
        self.assertEquals(self.machine_function_mock.call_count, 1)
        self.machine_function_mock.call_count = 0

        # New machine picks up the failed task
        execute(self.project.id, self.step.slug)
        self._assert_correct_machine_task_state(
            TaskAssignment.Status.SUBMITTED, Task.Status.COMPLETE)

    def test_aborted_project(self):
        self._reset_task()
        self.project.status = Project.Status.ABORTED
        self.project.save()
        self.task.status = Task.Status.PROCESSING
        self.task.save()
        execute(self.project.id, self.step.slug)
        self._assert_correct_machine_task_state(
            TaskAssignment.Status.SUBMITTED, Task.Status.ABORTED)
