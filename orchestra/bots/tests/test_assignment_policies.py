from unittest.mock import patch

from orchestra.models import Iteration
from orchestra.models import Task
from orchestra.models import StaffBotRequest
from orchestra.models import StaffingRequestInquiry

from orchestra.communication.staffing import send_staffing_requests
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.utils.task_lifecycle import assign_task
from orchestra.utils.task_lifecycle import create_subsequent_tasks
from orchestra.utils.task_lifecycle import submit_task


class StaffBotAutoAssignTestCase(OrchestraTestCase):

    def setUp(self):
        super().setUp()
        setup_models(self)

    @patch('orchestra.bots.staffbot.send_mail')
    @patch('orchestra.bots.staffbot.StaffBot._send_staffing_request_by_slack')
    def test_preassign_workers(self, mock_mail, mock_slack):
        request_cause = StaffBotRequest.RequestCause.AUTOSTAFF.value
        staffing_request_count = StaffingRequestInquiry.objects.filter(
            request__request_cause=request_cause).count()
        project = self.projects['staffbot_assignment_policy']

        # Create first task in test project
        create_subsequent_tasks(project)
        send_staffing_requests()
        self.assertEqual(project.tasks.count(), 1)
        # Assign initial task to worker 0
        initial_task = assign_task(self.workers[0].id,
                                   project.tasks.first().id)
        # Submit task; next task should be created
        with patch('orchestra.utils.task_lifecycle._is_review_needed',
                   return_value=False):
            initial_task = submit_task(initial_task.id, {},
                                       Iteration.Status.REQUESTED_REVIEW,
                                       self.workers[0])

        # Mock mail should be called if we autostaff
        self.assertTrue(mock_mail.called)
        self.assertTrue(mock_slack.called)
        # Assert we created new StaffingRequestInquirys because of autostaff
        new_staffing_request_count = StaffingRequestInquiry.objects.filter(
            request__request_cause=request_cause).count()
        self.assertTrue(staffing_request_count < new_staffing_request_count)
        self.assertEqual(project.tasks.count(), 2)
        related_task = project.tasks.exclude(id=initial_task.id).first()
        # Worker 0 not certified for related tasks, so should not have been
        # auto-assigned
        self.assertEqual(related_task.assignments.count(), 0)
        self.assertEqual(related_task.status, Task.Status.AWAITING_PROCESSING)

        # Reset project
        project.tasks.all().delete()
