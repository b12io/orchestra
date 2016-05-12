from unittest.mock import patch

from django.conf import settings
from django.test import override_settings

from orchestra.communication.mail import send_mail
from orchestra.models import CommunicationPreference
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import setup_models


class ModelsTestCase(OrchestraTestCase):

    def setUp(self):
        super().setUp()
        setup_models(self)
        self.worker = self.workers[0]
        self.comm_type = (CommunicationPreference.CommunicationType
                          .TASK_STATUS_CHANGE.value)
        self.recipient_list = [self.worker.user.email]

    @patch('orchestra.communication.mail._send_mail')
    def test_filtering_no_preference(self, mock_mail):
        """
            Verify that we correctly filter users based on their email
            preferences.
        """
        # Test when no comm_type is given
        send_mail(subject='test_subject',
                  message='test_message',
                  from_email='test@test.com',
                  recipient_list=self.recipient_list
                  )
        mock_mail.assert_called_once_with(
            'test_subject', 'test_message',
            'test@test.com', self.recipient_list,
            fail_silently=False, auth_user=None,
            auth_password=None, connection=None,
            html_message=None
        )

    @override_settings(ORCHESTRA_MOCK_TO_EMAIL='to-email@test.com')
    @override_settings(ORCHESTRA_MOCK_EMAILS=True)
    @patch('orchestra.communication.mail._send_mail')
    def test_email_mocked(self, mock_mail):
        """
            Verify that we mock email sending.
        """
        # Test when no comm_type is given
        send_mail(subject='test_subject',
                  message='test_message',
                  from_email='test@test.com',
                  recipient_list=self.recipient_list,
                  )
        mock_mail.assert_called_once_with(
            'test_subject', 'test_message',
            'test@test.com', [settings.ORCHESTRA_MOCK_TO_EMAIL],
            fail_silently=False, auth_user=None,
            auth_password=None, connection=None,
            html_message=None
        )

    @patch('orchestra.communication.mail._send_mail')
    def test_filtering_send_with_preference(self, mock_mail):
        # Test when comm_type is allowed
        send_mail(subject='test_subject',
                  message='test_message',
                  from_email='test@test.com',
                  recipient_list=self.recipient_list,
                  communication_type=self.comm_type
                  )
        mock_mail.assert_called_once_with(
            'test_subject', 'test_message',
            'test@test.com', self.recipient_list,
            fail_silently=False, auth_user=None,
            auth_password=None, connection=None,
            html_message=None
        )

    @patch('orchestra.communication.mail._send_mail')
    def test_filtering_no_send(self, mock_mail):
        # Test when comm_type is not allowed
        comm_pref = CommunicationPreference.objects.get(
            worker=self.worker,
            communication_type=self.comm_type
        )
        comm_pref.methods.email = ~CommunicationPreference.methods.email
        comm_pref.save()
        self.assertFalse(comm_pref.can_email())
        send_mail(subject='test_subject',
                  message='test_message',
                  from_email='test@test.com',
                  recipient_list=self.recipient_list,
                  communication_type=self.comm_type
                  )
        self.assertFalse(mock_mail.called)
