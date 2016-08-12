from datetime import timedelta
from django.utils import timezone
from unittest.mock import patch

from orchestra.bots.errors import StaffingResponseException
from orchestra.communication.staffing import get_available_requests
from orchestra.communication.staffing import handle_staffing_response
from orchestra.communication.staffing import send_staffing_requests
from orchestra.models import CommunicationPreference
from orchestra.models import StaffBotRequest
from orchestra.models import StaffingRequestInquiry
from orchestra.models import StaffingResponse
from orchestra.models import TaskAssignment
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import CommunicationPreferenceFactory
from orchestra.tests.helpers.fixtures import StaffBotRequestFactory
from orchestra.tests.helpers.fixtures import StaffingRequestInquiryFactory
from orchestra.tests.helpers.fixtures import WorkerFactory


class StaffingTestCase(OrchestraTestCase):

    def setUp(self):
        self.worker = WorkerFactory()
        self.staffing_request_inquiry = StaffingRequestInquiryFactory(
            communication_preference__worker=self.worker,
            communication_preference__communication_type=(
                CommunicationPreference.CommunicationType
                .NEW_TASK_AVAILABLE.value),
            request__task__step__is_human=True
        )
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
        self.assertEqual(response.request_inquiry.request.status,
                         StaffBotRequest.Status.COMPLETE.value)
        self.assertEqual(StaffingResponse.objects.all().count(), old_count + 1)

        task_assignment = (
            TaskAssignment.objects
            .get(worker=self.worker,
                 task=self.staffing_request_inquiry.request.task))
        self.assertEquals(task_assignment.status,
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
        self.assertEquals(task_assignment.status,
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
        self.assertEquals(task_assignment.worker, worker2)

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

        request = StaffBotRequestFactory()
        self.assertEquals(request.status,
                          StaffBotRequest.Status.PROCESSING.value)

        send_staffing_requests(worker_batch_size=1,
                               frequency=timedelta(minutes=0))
        mock_slack.assert_not_called()
        request.refresh_from_db()
        self.assertEquals(request.status,
                          StaffBotRequest.Status.PROCESSING.value)
        # Inquiries increase by two because we send a Slack and an
        # email notification.
        self.assertEquals(
            StaffingRequestInquiry.objects.filter(request=request).count(),
            2)

        send_staffing_requests(worker_batch_size=1,
                               frequency=timedelta(minutes=0))
        mock_slack.assert_not_called()
        request.refresh_from_db()
        self.assertEquals(request.status,
                          StaffBotRequest.Status.PROCESSING.value)
        self.assertEquals(
            StaffingRequestInquiry.objects.filter(request=request).count(),
            4)

        # marked as complete and no new request inquiries sent.
        send_staffing_requests(worker_batch_size=1,
                               frequency=timedelta(minutes=0))
        self.assertTrue(mock_slack.called)
        request.refresh_from_db()
        self.assertEquals(request.status,
                          StaffBotRequest.Status.COMPLETE.value)
        self.assertEquals(
            StaffingRequestInquiry.objects.filter(request=request).count(),
            4)

    @patch('orchestra.communication.staffing.message_experts_slack_group')
    def test_send_staffing_request_priorities(self, mock_slack):

        worker2 = WorkerFactory(staffing_priority=-1)
        CommunicationPreferenceFactory(
            worker=worker2,
            communication_type=(
                CommunicationPreference.CommunicationType
                .NEW_TASK_AVAILABLE.value))

        worker3 = WorkerFactory(staffing_priority=1)
        CommunicationPreferenceFactory(
            worker=worker3,
            communication_type=(
                CommunicationPreference.CommunicationType
                .NEW_TASK_AVAILABLE.value))

        request = StaffBotRequestFactory()
        self.assertEquals(request.status,
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
                self.assertEquals(worker.id,
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
        mock_slack.assert_not_called()

        handle_staffing_response(
            worker2, self.staffing_request_inquiry.id,
            is_available=False)

        self.assertTrue(mock_slack.called)

    @patch('orchestra.communication.staffing.message_experts_slack_group')
    def test_get_available_request(self, mock_slack):
        # Complete all open requests so new worker doesn't receive them.
        send_staffing_requests(worker_batch_size=2,
                               frequency=timedelta(minutes=0))

        self.assertEquals(len(get_available_requests(self.worker)), 1)

        worker2 = WorkerFactory()
        CommunicationPreferenceFactory(
            worker=worker2,
            communication_type=(
                CommunicationPreference.CommunicationType
                .NEW_TASK_AVAILABLE.value))
        request1 = StaffBotRequestFactory(task__step__is_human=True)
        request2 = StaffBotRequestFactory(task__step__is_human=True)

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
        self.assertEquals(len(available_requests), 3)
        self.assertEquals(len(get_available_requests(worker2)), 2)

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
        self.assertEquals(len(get_available_requests(self.worker)), 2)
        self.assertEquals(len(get_available_requests(worker2)), 2)

        # `self.worker` will lose an available task (they ignore it),
        # whereas `worker2` is unchanged.
        handle_staffing_response(
            self.worker, inquiry1.id,
            is_available=False)
        self.assertEquals(len(get_available_requests(self.worker)), 1)
        self.assertEquals(len(get_available_requests(worker2)), 2)

        # `worker2` takes a task.
        handle_staffing_response(
            worker2, inquiry2.id,
            is_available=True)
        self.assertEquals(len(get_available_requests(self.worker)), 0)
        self.assertEquals(len(get_available_requests(worker2)), 1)

    @patch('orchestra.communication.staffing.message_experts_slack_group')
    def test_send_staffing_requests_parameters(self, mock_slack):
        for idx in range(5):
            CommunicationPreferenceFactory(
                worker=WorkerFactory(),
                communication_type=(
                    CommunicationPreference.CommunicationType
                    .NEW_TASK_AVAILABLE.value))
        # Make a new request and turn off the global request, as the
        # global one has an inquiry on it already.
        request = StaffBotRequestFactory(task__step__is_human=True)
        self.staffing_request_inquiry.request.status = (
            StaffBotRequest.Status.COMPLETE)

        send_staffing_requests(worker_batch_size=1,
                               frequency=timedelta(minutes=20))
        # Inquiries increase by two because we send a Slack and an
        # email notification.  `last_inquiry_sent` is None on new
        # tasks, so we send this batch regardless of frequency.
        self.assertEquals(
            StaffingRequestInquiry.objects.filter(request=request).count(),
            2)

        send_staffing_requests(worker_batch_size=2,
                               frequency=timedelta(minutes=20))
        # Don't send more inquiries, since it hasn't been 20 minutes.
        self.assertEquals(
            StaffingRequestInquiry.objects.filter(request=request).count(),
            2)

        request.last_inquiry_sent = timezone.now() - timedelta(minutes=21)
        request.save()
        send_staffing_requests(worker_batch_size=2,
                               frequency=timedelta(minutes=20))
        # Send two email and two slack inquiries since it's been 21 minutes.
        self.assertEquals(
            StaffingRequestInquiry.objects.filter(request=request).count(),
            6)

        send_staffing_requests(worker_batch_size=10,
                               frequency=timedelta(minutes=20))
        # Don't send more inquiries, since it hasn't been 20 minutes.
        self.assertEquals(
            StaffingRequestInquiry.objects.filter(request=request).count(),
            6)

        request.last_inquiry_sent = timezone.now() - timedelta(minutes=21)
        request.save()
        send_staffing_requests(worker_batch_size=10,
                               frequency=timedelta(minutes=20))
        # Send remaining inquiries, since enough time has passed.
        self.assertEquals(
            StaffingRequestInquiry.objects.filter(request=request).count(),
            12)

        request.last_inquiry_sent = timezone.now() - timedelta(minutes=21)
        request.save()
        send_staffing_requests(worker_batch_size=10,
                               frequency=timedelta(minutes=20))
        # We're all out of workers to whom we'd like to send inquiries.
        self.assertEquals(
            StaffingRequestInquiry.objects.filter(request=request).count(),
            12)
