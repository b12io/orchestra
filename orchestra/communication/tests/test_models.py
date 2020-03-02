from orchestra.accounts.signals import orchestra_user_registered
from orchestra.models import CommunicationPreference
from orchestra.tests.helpers import OrchestraModelTestCase
from orchestra.tests.helpers.fixtures import CommunicationPreferenceFactory
from orchestra.tests.helpers.fixtures import StaffBotRequestFactory
from orchestra.tests.helpers.fixtures import StaffingRequestInquiryFactory
from orchestra.tests.helpers.fixtures import StaffingResponseFactory
from orchestra.tests.helpers.fixtures import UserFactory


class CommunicationPreferenceTestCase(OrchestraModelTestCase):
    __test__ = True
    model = CommunicationPreferenceFactory

    def setUp(self):
        # Create a user

        self.comm_pref = CommunicationPreferenceFactory()

    def test_can_slack(self):
        """
            Assert that the object respects the slack bit field settings.
        """
        self.assertTrue(self.comm_pref.can_slack())

        self.comm_pref.methods.slack = False
        self.assertFalse(self.comm_pref.can_slack())

    def test_can_email(self):
        """
            Assert that the object respects the email bit field settings.
        """
        self.assertTrue(self.comm_pref.can_email())

        self.comm_pref.methods.email = False
        self.assertFalse(self.comm_pref.can_email())

    def test_communication_preference_autocreation(self):
        """
            When new users register, CommunicationPreferences should be
            automatically created .
        """

        # Create a user
        user = UserFactory(username='test_registration_user',
                           password='test',
                           email='test_registration_user@test.com')

        # There should be no preferences yet
        self.assertFalse(CommunicationPreference.objects.filter(
            worker__user=user).exists())

        # Fake registering the user
        orchestra_user_registered.send(
            sender=self.__class__, user=user, request=None)

        # Expect the worker object to be created
        self.assertTrue(
            CommunicationPreference.objects.filter(worker__user=user).exists(),
            'CommunicationPreference not autocreated on User registration'
        )

        comm_prefs = CommunicationPreference.objects.filter(worker__user=user)
        self.assertEqual(comm_prefs.count(), len(
            CommunicationPreference.CommunicationType.choices()))

        for comm_pref in comm_prefs:
            for label, flag in comm_pref.methods.iteritems():
                self.assertTrue(flag)


class StaffBotRequestTestCase(OrchestraModelTestCase):
    __test__ = True
    model = StaffBotRequestFactory

    def test_is_request_open(self):
        staffbot_request = StaffBotRequestFactory()

        staffing_inquiry_1 = StaffingRequestInquiryFactory(
            request=staffbot_request)
        staffing_inquiry_2 = StaffingRequestInquiryFactory(
            request=staffbot_request)
        staffing_response_1 = StaffingResponseFactory(
            request_inquiry=staffing_inquiry_1,
            is_winner=False)
        self.assertEqual(staffbot_request.is_open(), True)

        # If there is a winner, the request is close.
        staffing_response_1.is_winner = True
        staffing_response_1.save()
        self.assertEqual(staffbot_request.is_open(), False)

        # If there is no winner after all've replied,
        # the request is close.
        staffing_response_1.is_winner = False
        staffing_response_1.save()
        StaffingResponseFactory(
            request_inquiry=staffing_inquiry_2,
            is_winner=False)
        self.assertEqual(staffbot_request.is_open(), False)

        # Only count one response per one inquiry.
        StaffingResponseFactory(
            request_inquiry=staffing_inquiry_2,
            is_winner=False)
        self.assertEqual(staffbot_request.is_open(), False)


class StaffingRequestInquiryTestCase(OrchestraModelTestCase):
    __test__ = True
    model = StaffingRequestInquiryFactory


class StaffingResponseTestCase(OrchestraModelTestCase):
    __test__ = True
    model = StaffingResponseFactory
