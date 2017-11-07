from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone

from orchestra.bots.errors import StaffingResponseException
from orchestra.communication.staffing import get_available_requests
from orchestra.communication.staffing import handle_staffing_response
from orchestra.communication.staffing import \
    remind_workers_about_available_tasks
from orchestra.communication.staffing import send_staffing_requests
from orchestra.communication.staffing import \
    warn_staffing_team_about_unstaffed_tasks
from orchestra.communication.utils import mark_worker_as_winner
from orchestra.models import CommunicationPreference
from orchestra.models import StaffBotRequest
from orchestra.models import StaffingRequestInquiry
from orchestra.models import StaffingResponse
from orchestra.models import TaskAssignment
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import CertificationFactory
from orchestra.tests.helpers.fixtures import CommunicationPreferenceFactory
from orchestra.tests.helpers.fixtures import StaffBotRequestFactory
from orchestra.tests.helpers.fixtures import StaffingRequestInquiryFactory
from orchestra.tests.helpers.fixtures import StaffingResponseFactory
from orchestra.tests.helpers.fixtures import WorkerCertificationFactory
from orchestra.tests.helpers.fixtures import WorkerFactory


class StaffingTestCase(OrchestraTestCase):

    def setUp(self):
        self.worker = WorkerFactory()
        self.certification = CertificationFactory()
        WorkerCertificationFactory(
            worker=self.worker,
            certification=self.certification
        )

        self.staffing_request_inquiry = StaffingRequestInquiryFactory(
            communication_preference__worker=self.worker,
            communication_preference__communication_type=(
                CommunicationPreference.CommunicationType
                .NEW_TASK_AVAILABLE.value),
            request__task__step__is_human=True
        )
        self.staffing_request_inquiry \
            .request.task.step.required_certifications.add(
                self.certification)
        super().setUp()

    def test_handle_staffing_response_invalid_request(self):
        old_count = StaffingResponse.objects.all().count()

        # Invalid staffing_request_inquiry_id
        response = handle_staffing_response(
            self.worker, None, is_available=True)
        self.assertEqual(response, None)
        self.assertEqual(StaffingResponse.objects.all().count(), old_count)

        # Invalid worker
        response = handle_staffing_response(
            None, self.staffing_request_inquiry.id, is_available=True)
        self.assertEqual(response, None)
        self.assertEqual(StaffingResponse.objects.all().count(), old_count)

    def test_handle_staffing_response_is_available(self):
        # Test StaffingResponse object creation
        old_count = StaffingResponse.objects.all().count()

        # assign task is called
        response = handle_staffing_response(
            self.worker, self.staffing_request_inquiry.id,
            is_available=True)
        self.assertTrue(response.is_winner)
        self.staffing_request_inquiry.refresh_from_db()
        self.assertEqual(response.request_inquiry.request.status,
                         StaffBotRequest.Status.COMPLETE.value)
        self.assertEqual(StaffingResponse.objects.all().count(), old_count + 1)

        task_assignment = (
            TaskAssignment.objects
            .get(worker=self.worker,
                 task=self.staffing_request_inquiry.request.task))
        self.assertEqual(task_assignment.status,
                         TaskAssignment.Status.PROCESSING)
        self.staffing_request_inquiry.request.task.refresh_from_db()

        # Replay of same request
        response = handle_staffing_response(
            self.worker, self.staffing_request_inquiry.id, is_available=True)
        self.assertTrue(response.is_winner)
        self.assertEqual(response.request_inquiry.request.status,
                         StaffBotRequest.Status.COMPLETE.value)
        self.assertEqual(StaffingResponse.objects.all().count(), old_count + 1)

        # Change mind to `is_available=False` does not do anything
        with self.assertRaises(StaffingResponseException):
            response = handle_staffing_response(
                self.worker, self.staffing_request_inquiry.id,
                is_available=False)

        new_request_inquiry = StaffingRequestInquiryFactory(
            request__task__step__is_human=True
        )
        new_worker = new_request_inquiry.communication_preference.worker
        old_count = StaffingResponse.objects.all().count()
        response = handle_staffing_response(
            new_worker, new_request_inquiry.id, is_available=True)
        self.assertTrue(response.is_winner)
        self.assertEqual(response.request_inquiry.request.status,
                         StaffBotRequest.Status.COMPLETE.value)
        self.assertEqual(StaffingResponse.objects.all().count(), old_count + 1)

        task_assignment = (
            TaskAssignment.objects
            .get(worker=new_worker,
                 task=new_request_inquiry.request.task))
        self.assertEqual(task_assignment.status,
                         TaskAssignment.Status.PROCESSING)

        # restaff
        response.is_winner = False
        response.save()

        worker2 = WorkerFactory()
        staffing_request_inquiry2 = StaffingRequestInquiryFactory(
            communication_preference__worker=worker2,
            request__task=new_request_inquiry.request.task
        )
        response = handle_staffing_response(
            worker2, staffing_request_inquiry2.id, is_available=True)
        self.assertTrue(response.is_winner)
        self.assertEqual(response.request_inquiry.request.status,
                         StaffBotRequest.Status.COMPLETE.value)
        task_assignment.refresh_from_db()
        self.assertEqual(task_assignment.worker, worker2)

    def test_handle_staffing_response_not_is_available(self):
        # Test StaffingResponse object creation
        old_count = StaffingResponse.objects.all().count()
        response = handle_staffing_response(
            self.worker, self.staffing_request_inquiry.id,
            is_available=False)
        self.assertFalse(response.is_winner)
        self.assertEqual(response.request_inquiry.request.status,
                         StaffBotRequest.Status.PROCESSING.value)
        self.assertEqual(StaffingResponse.objects.all().count(), old_count + 1)

        # Replay of same request
        response = handle_staffing_response(
            self.worker, self.staffing_request_inquiry.id,
            is_available=False)
        self.assertFalse(response.is_winner)
        self.assertEqual(response.request_inquiry.request.status,
                         StaffBotRequest.Status.PROCESSING.value)
        self.assertEqual(StaffingResponse.objects.all().count(), old_count + 1)

        # Change mind to `is_available=True`
        response = handle_staffing_response(
            self.worker, self.staffing_request_inquiry.id,
            is_available=True)
        self.assertTrue(response.is_winner)
        self.assertEqual(response.request_inquiry.request.status,
                         StaffBotRequest.Status.COMPLETE.value)
        self.assertEqual(StaffingResponse.objects.all().count(), old_count + 1)

        # Task is not available to claim
        new_request_inquiry = StaffingRequestInquiryFactory(
            request=self.staffing_request_inquiry.request,
            request__task__step__is_human=True)
        new_worker = new_request_inquiry.communication_preference.worker
        old_count = StaffingResponse.objects.all().count()
        response = handle_staffing_response(
            new_worker, new_request_inquiry.id, is_available=True)
        self.assertFalse(response.is_winner)
        self.assertEqual(response.request_inquiry.request.status,
                         StaffBotRequest.Status.COMPLETE.value)
        self.assertEqual(StaffingResponse.objects.all().count(), old_count + 1)

    @patch('orchestra.communication.staffing.message_experts_slack_group')
    def test_send_staffing_requests(self, mock_slack):
        worker2 = WorkerFactory()
        CommunicationPreferenceFactory(
            worker=worker2,
            communication_type=(
                CommunicationPreference.CommunicationType
                .NEW_TASK_AVAILABLE.value))
        WorkerCertificationFactory(
            worker=worker2,
            certification=self.certification
        )

        request = StaffBotRequestFactory()
        request.task.step.required_certifications.add(self.certification)

        self.assertEqual(request.status,
                         StaffBotRequest.Status.PROCESSING.value)

        send_staffing_requests(worker_batch_size=1,
                               frequency=timedelta(minutes=0))
        mock_slack.assert_not_called()
        request.refresh_from_db()
        self.assertEqual(request.status,
                         StaffBotRequest.Status.PROCESSING.value)
        # Inquiries increase by two because we send a Slack and an
        # email notification.
        self.assertEqual(
            StaffingRequestInquiry.objects.filter(request=request).count(),
            2)

        send_staffing_requests(worker_batch_size=1,
                               frequency=timedelta(minutes=0))
        self.assertEqual(mock_slack.call_count, 1)
        mock_slack.reset()

        request.refresh_from_db()
        self.assertEqual(request.status,
                         StaffBotRequest.Status.PROCESSING.value)
        self.assertEqual(
            StaffingRequestInquiry.objects.filter(request=request).count(),
            4)

        # marked as complete and no new request inquiries sent.
        send_staffing_requests(worker_batch_size=1,
                               frequency=timedelta(minutes=0))
        self.assertTrue(mock_slack.called)
        request.refresh_from_db()
        self.assertEqual(request.status,
                         StaffBotRequest.Status.COMPLETE.value)
        self.assertEqual(
            StaffingRequestInquiry.objects.filter(request=request).count(),
            4)

    @patch('orchestra.communication.staffing.message_experts_slack_group')
    def test_send_staffing_request_priorities(self, mock_slack):

        worker2 = WorkerFactory()
        WorkerCertificationFactory(worker=worker2,
                                   staffing_priority=-1)

        CommunicationPreferenceFactory(
            worker=worker2,
            communication_type=(
                CommunicationPreference.CommunicationType
                .NEW_TASK_AVAILABLE.value))

        worker3 = WorkerFactory()
        WorkerCertificationFactory(worker=worker3,
                                   staffing_priority=1)
        CommunicationPreferenceFactory(
            worker=worker3,
            communication_type=(
                CommunicationPreference.CommunicationType
                .NEW_TASK_AVAILABLE.value))

        request = StaffBotRequestFactory()
        self.assertEqual(request.status,
                         StaffBotRequest.Status.PROCESSING.value)

        # Workers should be contacted in priority order.
        excluded = []
        for worker in (worker3, self.worker, worker2):
            send_staffing_requests(worker_batch_size=1,
                                   frequency=timedelta(minutes=0))
            inquiries = (
                StaffingRequestInquiry.objects
                .filter(request=request)
                .exclude(communication_preference__worker__in=excluded))
            for inquiry in inquiries:
                self.assertEqual(worker.id,
                                 inquiry.communication_preference.worker.id)
            excluded.append(worker)

    @patch('orchestra.communication.staffing.message_experts_slack_group')
    def test_handle_staffing_response_all_rejected(self, mock_slack):
        worker2 = WorkerFactory()

        CommunicationPreferenceFactory(
            worker=worker2,
            communication_type=(
                CommunicationPreference.CommunicationType
                .NEW_TASK_AVAILABLE.value))

        response = handle_staffing_response(
            self.worker, self.staffing_request_inquiry.id,
            is_available=False)
        self.assertFalse(response.is_winner)
        self.assertEqual(response.request_inquiry.request.status,
                         StaffBotRequest.Status.PROCESSING.value)
        self.assertEqual(mock_slack.call_count, 1)
        mock_slack.reset()

        handle_staffing_response(
            worker2, self.staffing_request_inquiry.id,
            is_available=False)

        self.assertEqual(mock_slack.call_count, 1)

    @patch('orchestra.communication.staffing.message_experts_slack_group')
    def test_get_available_request(self, mock_slack):
        # Complete all open requests so new worker doesn't receive them.
        send_staffing_requests(worker_batch_size=2,
                               frequency=timedelta(minutes=0))

        self.assertEqual(len(get_available_requests(self.worker)), 1)

        worker2 = WorkerFactory()
        CommunicationPreferenceFactory(
            worker=worker2,
            communication_type=(
                CommunicationPreference.CommunicationType
                .NEW_TASK_AVAILABLE.value))
        WorkerCertificationFactory(
            worker=worker2,
            certification=self.certification
        )

        request1 = StaffBotRequestFactory(task__step__is_human=True)
        request1.task.step.required_certifications.add(self.certification)
        request2 = StaffBotRequestFactory(task__step__is_human=True)
        request2.task.step.required_certifications.add(self.certification)

        send_staffing_requests(worker_batch_size=2,
                               frequency=timedelta(minutes=0))
        inquiry1 = (
            StaffingRequestInquiry.objects
            .filter(communication_preference__worker=self.worker)
            .filter(request=request1).first())
        inquiry2 = (
            StaffingRequestInquiry.objects
            .filter(communication_preference__worker=worker2)
            .filter(request=request2).first())

        # `self.worker` now has three available tasks, whereas `worker2`
        # just has access to the two new tasks.
        available_requests = get_available_requests(self.worker)
        self.assertEqual(len(available_requests), 3)
        self.assertEqual(len(get_available_requests(worker2)), 2)

        # Tasks should be sorted by start_datetime in ascending order.

        first_task, second_task, third_task = (
            available_requests[0]['task'], available_requests[1]['task'],
            available_requests[2]['task'])
        self.assertLess(
            first_task.start_datetime, second_task.start_datetime)
        self.assertLess(
            second_task.start_datetime, third_task.start_datetime)

        # `self.worker` will lose an available task (they accept it),
        # whereas `worker2` is unchanged.
        handle_staffing_response(
            self.worker, self.staffing_request_inquiry.id,
            is_available=True)
        self.assertEqual(len(get_available_requests(self.worker)), 2)
        self.assertEqual(len(get_available_requests(worker2)), 2)

        # `self.worker` will lose an available task (they ignore it),
        # whereas `worker2` is unchanged.
        handle_staffing_response(
            self.worker, inquiry1.id,
            is_available=False)
        self.assertEqual(len(get_available_requests(self.worker)), 1)
        self.assertEqual(len(get_available_requests(worker2)), 2)

        # `worker2` takes a task.
        handle_staffing_response(
            worker2, inquiry2.id,
            is_available=True)
        self.assertEqual(len(get_available_requests(self.worker)), 0)
        self.assertEqual(len(get_available_requests(worker2)), 1)

    @patch('orchestra.communication.staffing.message_internal_slack_group')
    def test_warn_staffing_team_about_unstaffed_tasks(self, mock_slack):
        warn_staffing_team_about_unstaffed_tasks()
        mock_slack.assert_not_called()

        create_time = timezone.now() - timedelta(minutes=31)
        StaffingResponseFactory(
            request_inquiry__request__task__start_datetime=create_time,
            request_inquiry__request__created_at=create_time,
            is_winner=False
        )
        warn_staffing_team_about_unstaffed_tasks()
        self.assertEqual(mock_slack.call_count, 1)

        args, _ = mock_slack.call_args
        self.assertTrue('No winner request for task' in args[1])

    @patch('orchestra.communication.staffing.StaffBot'
           '._send_staffing_request_by_mail')
    @patch('orchestra.communication.staffing.StaffBot'
           '._send_staffing_request_by_slack')
    def test_remind_workers_about_available_tasks(self, mock_slack, mock_mail):
        # mark existing request as a winner
        staffing_response = StaffingResponse.objects.create(
            request_inquiry=self.staffing_request_inquiry,
            is_available=True,
            is_winner=True)

        remind_workers_about_available_tasks()
        mock_slack.assert_not_called()

        staffing_response.delete()

        remind_workers_about_available_tasks()
        self.assertEqual(mock_slack.call_count, 1)

        args, _ = mock_slack.call_args
        self.assertTrue(
            'Tasks are still available for you to work on' in args[1])
        # No href in slack
        self.assertTrue(
            '<a href' not in args[1])

        args, _ = mock_mail.call_args
        self.assertTrue(
            'Tasks are still available for you to work on' in args[1])
        # href in email
        self.assertTrue(
            '<a href' in args[1])

    def test_mark_worker_as_winner(self):
        self.assertEqual(
            self.staffing_request_inquiry.responses.all().count(), 0)

        mark_worker_as_winner(self.worker,
                              self.staffing_request_inquiry.request.task,
                              0,
                              self.staffing_request_inquiry)
        staffbot_request = self.staffing_request_inquiry.request
        staffbot_request.refresh_from_db()

        self.assertEqual(staffbot_request.status,
                         StaffBotRequest.Status.COMPLETE.value)
        self.assertEqual(
            self.staffing_request_inquiry.responses.all().count(), 1)

        response = self.staffing_request_inquiry.responses.first()
        self.assertTrue(response.is_winner)

        response.is_winner = False
        response.is_available = False
        mark_worker_as_winner(self.worker,
                              self.staffing_request_inquiry.request.task,
                              0, None)
        self.assertEqual(
            self.staffing_request_inquiry.responses.all().count(), 1)
        response.refresh_from_db()
        self.assertTrue(response.is_winner)

    @patch('orchestra.communication.staffing.message_experts_slack_group')
    def test_send_staffing_requests_parameters(self, mock_slack):
        for idx in range(5):
            worker = WorkerFactory()
            CommunicationPreferenceFactory(
                worker=worker,
                communication_type=(
                    CommunicationPreference.CommunicationType
                    .NEW_TASK_AVAILABLE.value))
            WorkerCertificationFactory(
                worker=worker,
                certification=self.certification
            )
        # Make a new request and turn off the global request, as the
        # global one has an inquiry on it already.
        request = StaffBotRequestFactory(task__step__is_human=True)
        request.task.step.required_certifications.add(self.certification)

        self.staffing_request_inquiry.request.status = (
            StaffBotRequest.Status.COMPLETE)

        send_staffing_requests(worker_batch_size=1,
                               frequency=timedelta(minutes=20))
        # Inquiries increase by two because we send a Slack and an
        # email notification.  `last_inquiry_sent` is None on new
        # tasks, so we send this batch regardless of frequency.
        self.assertEqual(
            StaffingRequestInquiry.objects.filter(request=request).count(),
            2)

        send_staffing_requests(worker_batch_size=2,
                               frequency=timedelta(minutes=20))
        # Don't send more inquiries, since it hasn't been 20 minutes.
        self.assertEqual(
            StaffingRequestInquiry.objects.filter(request=request).count(),
            2)

        request.last_inquiry_sent = timezone.now() - timedelta(minutes=21)
        request.save()
        send_staffing_requests(worker_batch_size=2,
                               frequency=timedelta(minutes=20))
        # Send two email and two slack inquiries since it's been 21 minutes.
        self.assertEqual(
            StaffingRequestInquiry.objects.filter(request=request).count(),
            6)

        send_staffing_requests(worker_batch_size=10,
                               frequency=timedelta(minutes=20))
        # Don't send more inquiries, since it hasn't been 20 minutes.
        self.assertEqual(
            StaffingRequestInquiry.objects.filter(request=request).count(),
            6)

        request.last_inquiry_sent = timezone.now() - timedelta(minutes=21)
        request.save()
        send_staffing_requests(worker_batch_size=10,
                               frequency=timedelta(minutes=20))
        # Send remaining inquiries, since enough time has passed.
        self.assertEqual(
            StaffingRequestInquiry.objects.filter(request=request).count(),
            12)

        request.last_inquiry_sent = timezone.now() - timedelta(minutes=21)
        request.save()
        send_staffing_requests(worker_batch_size=10,
                               frequency=timedelta(minutes=20))
        # We're all out of workers to whom we'd like to send inquiries.
        self.assertEqual(
            StaffingRequestInquiry.objects.filter(request=request).count(),
            12)
