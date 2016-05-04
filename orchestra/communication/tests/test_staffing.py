from orchestra.communication.staffing import handle_staffing_response
from orchestra.models import StaffingResponse
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import StaffingRequestFactory
from orchestra.tests.helpers.fixtures import WorkerFactory


class StaffingTestCase(OrchestraTestCase):

    def setUp(self):
        self.worker = WorkerFactory()
        self.staffing_request = StaffingRequestFactory(
            communication_preference__worker=self.worker,
            task__step__is_human=True
        )
        super().setUp()

    def test_handle_staffing_response_invalid_request(self):
        old_count = StaffingResponse.objects.all().count()

        # Invalid staffing_request_id
        response = handle_staffing_response(
            self.worker, None, is_available=True)
        self.assertEqual(response, None)
        self.assertEqual(StaffingResponse.objects.all().count(), old_count)

        # Invalid worker
        response = handle_staffing_response(
            None, self.staffing_request.id, is_available=True)
        self.assertEqual(response, None)
        self.assertEqual(StaffingResponse.objects.all().count(), old_count)

    def test_handle_staffing_response_is_available(self):
        # Test StaffingResponse object creation
        old_count = StaffingResponse.objects.all().count()
        response = handle_staffing_response(
            self.worker, self.staffing_request.id, is_available=True)
        self.assertTrue(response.is_winner)
        self.assertEqual(StaffingResponse.objects.all().count(), old_count + 1)

        task_assignment = (TaskAssignment.objects
                           .get(worker=self.worker,
                                task=self.staffing_request.task))
        self.assertEquals(task_assignment.status,
                          TaskAssignment.Status.PROCESSING)
        self.staffing_request.task.refresh_from_db()

        self.assertEquals(self.staffing_request.task.status,
                          Task.Status.PROCESSING)

        # Replay of same request
        response = handle_staffing_response(
            self.worker, self.staffing_request.id, is_available=True)
        self.assertTrue(response.is_winner)
        self.assertEqual(StaffingResponse.objects.all().count(), old_count + 1)

        # Change mind to `is_available=False`
        response = handle_staffing_response(
            self.worker, self.staffing_request.id, is_available=False)
        self.assertFalse(response.is_winner)
        self.assertEqual(StaffingResponse.objects.all().count(), old_count + 1)
        task_assignment.refresh_from_db()
        self.assertEquals(task_assignment.status, TaskAssignment.Status.FAILED)
        self.staffing_request.task.refresh_from_db()

        # Task is available to claim
        self.assertEquals(self.staffing_request.task.status,
                          Task.Status.AWAITING_PROCESSING)

        new_staffing_request = StaffingRequestFactory(
            task__step__is_human=True
        )
        new_worker = new_staffing_request.communication_preference.worker
        old_count = StaffingResponse.objects.all().count()
        response = handle_staffing_response(
            new_worker, new_staffing_request.id, is_available=True)
        self.assertTrue(response.is_winner)
        self.assertEqual(StaffingResponse.objects.all().count(), old_count + 1)

    def test_handle_staffing_response_not_is_available(self):
        # Test StaffingResponse object creation
        old_count = StaffingResponse.objects.all().count()
        response = handle_staffing_response(
            self.worker, self.staffing_request.id, is_available=False)
        self.assertFalse(response.is_winner)
        self.assertEqual(StaffingResponse.objects.all().count(), old_count + 1)

        # Replay of same request
        response = handle_staffing_response(
            self.worker, self.staffing_request.id, is_available=False)
        self.assertFalse(response.is_winner)
        self.assertEqual(StaffingResponse.objects.all().count(), old_count + 1)

        # Change mind to `is_available=True`
        response = handle_staffing_response(
            self.worker, self.staffing_request.id, is_available=True)
        self.assertTrue(response.is_winner)
        self.assertEqual(StaffingResponse.objects.all().count(), old_count + 1)

        # Task is not available to claim
        new_staffing_request = StaffingRequestFactory()
        new_worker = new_staffing_request.communication_preference.worker
        old_count = StaffingResponse.objects.all().count()
        response = handle_staffing_response(
            new_worker, new_staffing_request.id, is_available=True)
        self.assertFalse(response.is_winner)
        self.assertEqual(StaffingResponse.objects.all().count(), old_count + 1)
