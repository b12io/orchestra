from django.core.urlresolvers import reverse

from orchestra.tests.helpers import OrchestraAuthenticatedTestCase
from orchestra.tests.helpers.fixtures import StaffingRequestFactory
from orchestra.tests.helpers.fixtures import StaffingResponseFactory


class StaffRequestTest(OrchestraAuthenticatedTestCase):

    def setUp(self):
        super().setUp()
        self.request_client, self.user = self.authenticate_user()
        self.staffing_request = StaffingRequestFactory(worker__user=self.user)
        self.staffing_response = StaffingResponseFactory()
        self.url_kwargs = {
            'staffing_request_id': self.staffing_request.pk
        }


class AcceptStaffRequestTest(StaffRequestTest):

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'orchestra:accept_staffing_request', kwargs=self.url_kwargs)

    def test_get(self):
        response = self.request_client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'communication/staffing_request_accepted.html')


class RejectStaffRequestTest(StaffRequestTest):

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'orchestra:reject_staffing_request', kwargs=self.url_kwargs)

    def test_get(self):
        response = self.request_client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'communication/staffing_request_rejected.html')
