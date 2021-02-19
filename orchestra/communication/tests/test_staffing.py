from datetime import timedelta
from unittest.mock import patch

from django.test import override_settings
from django.utils import timezone

from orchestra.bots.errors import StaffingResponseException
from orchestra.communication.staffing import get_available_requests
from orchestra.communication.staffing import handle_staffing_response
from orchestra.communication.staffing import \
    remind_workers_about_available_tasks
from orchestra.communication.staffing import address_staffing_requests
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
from orchestra.tests.helpers.fixtures import TimeEntryFactory
from orchestra.tests.helpers.fixtures import WorkerAvailabilityFactory
from orchestra.tests.helpers.fixtures import WorkerCertificationFactory
from orchestra.tests.helpers.fixtures import WorkerFactory


def _get_assignable_hours_for_task(task_data):
    return 3


class StaffingTestCase(OrchestraTestCase):

    def setUp(self):
        self.certification = CertificationFactory()
        self.worker, communication_preference = self._create_worker(0)
        self.staffing_request_inquiry = self._create_inquired_staffing_request(
            self.worker, communication_preference, False)

        super().setUp()

    def _create_worker(self, staffing_priority):
        worker = WorkerFactory()
        WorkerCertificationFactory(
            worker=worker,
            certification=self.certification,
            staffing_priority=staffing_priority
        )
        communication_preference = CommunicationPreferenceFactory(
            worker=worker,
            communication_type=(
                CommunicationPreference.CommunicationType
                .NEW_TASK_AVAILABLE.value))
        return worker, communication_preference

    def _create_inquired_staffing_request(
            self, worker, communication_preference, is_won):
        staffing_request_inquiry = StaffingRequestInquiryFactory(
            communication_preference=communication_preference,
            request__task__step__is_human=True,
            request__status=(
                StaffBotRequest.Status.CLOSED.value
                if is_won else StaffBotRequest.Status.SENDING_INQUIRIES.value)
        )
        staffing_request_inquiry \
            .request.task.step.required_certifications.add(
                self.certification)
        staffing_request = staffing_request_inquiry.request
        staffing_request.task.step.assignable_hours_function = {
            'path': ('orchestra.communication.tests'
                     '.test_staffing._get_assignable_hours_for_task')
        }
        staffing_request.task.step.save()
        if is_won:
            StaffingResponseFactory(
                request_inquiry=staffing_request_inquiry,
                is_available=True,
                is_winner=True)
        return staffing_request_inquiry

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
                         StaffBotRequest.Status.CLOSED.value)
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
                         StaffBotRequest.Status.CLOSED.value)
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
                         StaffBotRequest.Status.CLOSED.value)
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
                         StaffBotRequest.Status.CLOSED.value)
        task_assignment.refresh_from_db()
        self.assertEqual(task_assignment.worker, worker2)

    def test_handle_staffing_response_not_is_available(self):
        # Test StaffingResponse object creation
        old_count = StaffingResponse.objects.all().count()
        request = self.staffing_request_inquiry.request
        new_request_inquiry = StaffingRequestInquiryFactory(
            request=request)
        response = handle_staffing_response(
            self.worker, self.staffing_request_inquiry.id,
            is_available=False)
        self.assertFalse(response.is_winner)
        self.assertEqual(response.request_inquiry.request.status,
                         StaffBotRequest.Status.SENDING_INQUIRIES.value)
        self.assertEqual(StaffingResponse.objects.all().count(), old_count + 1)

        # Replay of same request
        response = handle_staffing_response(
            self.worker, self.staffing_request_inquiry.id,
            is_available=False)
        self.assertFalse(response.is_winner)
        self.assertEqual(response.request_inquiry.request.status,
                         StaffBotRequest.Status.SENDING_INQUIRIES.value)
        self.assertEqual(StaffingResponse.objects.all().count(), old_count + 1)

        # Change mind to `is_available=True`
        response = handle_staffing_response(
            self.worker, self.staffing_request_inquiry.id,
            is_available=True)
        self.assertTrue(response.is_winner)
        self.assertEqual(response.request_inquiry.request.status,
                         StaffBotRequest.Status.CLOSED.value)
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
                         StaffBotRequest.Status.CLOSED.value)
        self.assertEqual(StaffingResponse.objects.all().count(), old_count + 1)

    @patch('orchestra.communication.staffing.message_experts_slack_group')
    def test_address_staffing_requests(self, mock_slack):
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
                         StaffBotRequest.Status.SENDING_INQUIRIES.value)

        address_staffing_requests(worker_batch_size=1,
                                  frequency=timedelta(minutes=0))
        mock_slack.assert_not_called()
        request.refresh_from_db()
        self.assertEqual(request.status,
                         StaffBotRequest.Status.SENDING_INQUIRIES.value)
        # Inquiries increase by two because we send a Slack and an
        # email notification.
        self.assertEqual(
            StaffingRequestInquiry.objects.filter(request=request).count(),
            2)

        address_staffing_requests(worker_batch_size=1,
                                  frequency=timedelta(minutes=0))
        self.assertEqual(mock_slack.call_count, 1)
        mock_slack.reset()

        request.refresh_from_db()
        self.assertEqual(request.status,
                         StaffBotRequest.Status.SENDING_INQUIRIES.value)
        self.assertEqual(
            StaffingRequestInquiry.objects.filter(request=request).count(),
            4)

        # marked as closed and no new request inquiries sent.
        address_staffing_requests(worker_batch_size=1,
                                  frequency=timedelta(minutes=0))
        self.assertTrue(mock_slack.called)
        request.refresh_from_db()
        self.assertEqual(request.status,
                         StaffBotRequest.Status.DONE_SENDING_INQUIRIES.value)
        self.assertEqual(
            StaffingRequestInquiry.objects.filter(request=request).count(),
            4)

    @patch('orchestra.communication.staffing.handle_staffing_response')
    @patch('orchestra.communication.staffing.message_experts_slack_group')
    def test_address_staffing_request_priorities(
            self, mock_slack, mock_handle):
        worker2, _ = self._create_worker(-1)
        worker3, communication_preference3 = self._create_worker(1)

        # Workers should be contacted in priority order.
        excluded = [self.worker]
        for worker in (worker3, worker2):
            address_staffing_requests(worker_batch_size=1,
                                      frequency=timedelta(minutes=0))
            inquiries = (
                StaffingRequestInquiry.objects
                .filter(request=self.staffing_request_inquiry.request)
                .exclude(communication_preference__worker__in=excluded))
            # One inquiry for each communication method
            self.assertEqual(inquiries.count(), 2)
            for inquiry in inquiries:
                self.assertEqual(worker.id,
                                 inquiry.communication_preference.worker.id)
            excluded.append(worker)

        def _set_hours_available(availability, hours):
            for day in ['mon', 'tues', 'wed', 'thurs', 'fri', 'sat', 'sun']:
                setattr(availability, 'hours_available_{}'.format(day), hours)
            availability.save()

        total_inquiries = StaffingRequestInquiry.objects.count()
        # The highest-priority Worker has availability (7 hours) but
        # has already done 2 hours of work today and has been
        # previously assigned a 3-hour task today, so shouldn't be
        # automatically assigned the task which is estimated to take 3
        # hours.
        worker3_availability = WorkerAvailabilityFactory(worker=worker3)
        _set_hours_available(worker3_availability, 7)
        worker3.max_autostaff_hours_per_day = 7
        worker3.save()
        TimeEntryFactory(worker=worker3,
                         date=timezone.now().date(),
                         time_worked=timedelta(hours=2))
        self._create_inquired_staffing_request(
            worker3, communication_preference3, True)
        total_inquiries += 1
        address_staffing_requests(worker_batch_size=1,
                                  frequency=timedelta(minutes=0))
        mock_handle.assert_not_called()
        self.assertEqual(
            total_inquiries, StaffingRequestInquiry.objects.count())

        # Despite wanting 9 hours of work, and the estimate of worked
        # hours and new hours being 8, their maximum allowed hours
        # aren't high enough, so they aren't assigned.
        _set_hours_available(worker3_availability, 9)
        address_staffing_requests(worker_batch_size=1,
                                  frequency=timedelta(minutes=0))
        mock_handle.assert_not_called()
        self.assertEqual(
            total_inquiries, StaffingRequestInquiry.objects.count())

        # The highest-priority Worker has availability! But they have
        # already been assigned a task, and the maximum tasks allowed
        # is 1, so they aren't assigned.
        with override_settings(ORCHESTRA_MAX_AUTOSTAFF_TASKS_PER_DAY=1):
            worker3.max_autostaff_hours_per_day = 9
            worker3.save()
            address_staffing_requests(worker_batch_size=1,
                                      frequency=timedelta(minutes=0))
            mock_handle.assert_not_called()
            self.assertEqual(
                total_inquiries, StaffingRequestInquiry.objects.count())

        # The stars have aligned! Our default max tasks is 4, which
        # means this worker can pick up the tasks!
        address_staffing_requests(worker_batch_size=1,
                                  frequency=timedelta(minutes=0))
        previously_opted_in_method = (
            StaffingRequestInquiry.CommunicationMethod
            .PREVIOUSLY_OPTED_IN.value)
        inquiries = StaffingRequestInquiry.objects.filter(
            communication_preference__worker=worker3,
            communication_method=previously_opted_in_method
        )
        self.assertEqual(inquiries.count(), 1)
        mock_handle.assert_called_once_with(
            worker3, inquiries.first().id, is_available=True)
        self.assertEqual(
            total_inquiries + 1, StaffingRequestInquiry.objects.count())

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
                         StaffBotRequest.Status.CLOSED.value)
        self.assertEqual(mock_slack.call_count, 1)
        mock_slack.reset()

        handle_staffing_response(
            worker2, self.staffing_request_inquiry.id,
            is_available=False)

        self.assertEqual(mock_slack.call_count, 1)

    @patch('orchestra.communication.staffing.message_experts_slack_group')
    def test_get_available_request(self, mock_slack):
        # Close all open requests so new worker doesn't receive them.
        address_staffing_requests(worker_batch_size=2,
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

        address_staffing_requests(worker_batch_size=2,
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

        first_available, second_available, third_available = (
            available_requests[0]['available_datetime'],
            available_requests[1]['available_datetime'],
            available_requests[2]['available_datetime'])
        self.assertLess(first_available, second_available)
        self.assertLess(second_available, third_available)

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
    def test_remind_workers_about_available_tasks_has_winner(
            self, mock_slack, mock_mail):
        # mark existing request as a winner
        StaffingResponse.objects.create(
            request_inquiry=self.staffing_request_inquiry,
            is_available=True,
            is_winner=True)

        remind_workers_about_available_tasks()
        mock_slack.assert_not_called()

    @patch('orchestra.communication.staffing.StaffBot'
           '._send_staffing_request_by_mail')
    @patch('orchestra.communication.staffing.StaffBot'
           '._send_staffing_request_by_slack')
    def test_remind_workers_about_available_tasks(self, mock_slack, mock_mail):
        # mark existing request as a winner
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
                         StaffBotRequest.Status.CLOSED.value)
        self.assertEqual(
            self.staffing_request_inquiry.responses.all().count(), 0)

        # Can't mark another worker as a winner for this request
        worker2 = WorkerFactory()
        inquiry2 = StaffingRequestInquiryFactory(
            communication_preference__worker=worker2,
            communication_preference__communication_type=(
                CommunicationPreference.CommunicationType
                .NEW_TASK_AVAILABLE.value),
            request__task__step__is_human=True,
            request=self.staffing_request_inquiry.request
        )
        mark_worker_as_winner(worker2,
                              inquiry2.request.task,
                              0,
                              inquiry2)
        self.assertEqual(inquiry2.responses.count(), 0)

    @patch('orchestra.communication.staffing.message_experts_slack_group')
    def test_address_staffing_requests_parameters(self, mock_slack):
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
            StaffBotRequest.Status.DONE_SENDING_INQUIRIES)

        address_staffing_requests(worker_batch_size=1,
                                  frequency=timedelta(minutes=20))
        # Inquiries increase by two because we send a Slack and an
        # email notification.  `last_inquiry_sent` is None on new
        # tasks, so we send this batch regardless of frequency.
        self.assertEqual(
            StaffingRequestInquiry.objects.filter(request=request).count(),
            2)

        address_staffing_requests(worker_batch_size=2,
                                  frequency=timedelta(minutes=20))
        # Don't send more inquiries, since it hasn't been 20 minutes.
        self.assertEqual(
            StaffingRequestInquiry.objects.filter(request=request).count(),
            2)

        request.last_inquiry_sent = timezone.now() - timedelta(minutes=21)
        request.save()
        address_staffing_requests(worker_batch_size=2,
                                  frequency=timedelta(minutes=20))
        # Send two email and two slack inquiries since it's been 21 minutes.
        self.assertEqual(
            StaffingRequestInquiry.objects.filter(request=request).count(),
            6)

        address_staffing_requests(worker_batch_size=10,
                                  frequency=timedelta(minutes=20))
        # Don't send more inquiries, since it hasn't been 20 minutes.
        self.assertEqual(
            StaffingRequestInquiry.objects.filter(request=request).count(),
            6)

        request.last_inquiry_sent = timezone.now() - timedelta(minutes=21)
        request.save()
        address_staffing_requests(worker_batch_size=10,
                                  frequency=timedelta(minutes=20))
        # Send remaining inquiries, since enough time has passed.
        self.assertEqual(
            StaffingRequestInquiry.objects.filter(request=request).count(),
            12)

        request.last_inquiry_sent = timezone.now() - timedelta(minutes=21)
        request.save()
        address_staffing_requests(worker_batch_size=10,
                                  frequency=timedelta(minutes=20))
        # We're all out of workers to whom we'd like to send inquiries.
        self.assertEqual(
            StaffingRequestInquiry.objects.filter(request=request).count(),
            12)
