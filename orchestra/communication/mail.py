from django.conf import settings
from django.core.mail import send_mail as _send_mail
from markdown2 import markdown

from orchestra.models import CommunicationPreference
from orchestra.models import Worker


def send_mail(subject, message, from_email,
              recipient_list, fail_silently=False,
              auth_user=None, auth_password=None,
              connection=None, html_message=None,
              communication_type=None):
    """
    Light wrapper over Django's send_mail which filters out recipients who
    opted out of using email via their `CommuncationPreference` object.
    If `mock_mail` is set to true, the email is sent to the `from_email` to
    allow for testing.
    """
    if communication_type is not None:
        recipient_list = [
            email for email in recipient_list
            if _can_email(communication_type, email)
        ]
    if settings.ORCHESTRA_MOCK_EMAILS:
        # Send the mail to as many people as we normally would
        recipient_list = [
            settings.ORCHESTRA_MOCK_TO_EMAIL] * len(recipient_list)
    if len(recipient_list):
        return _send_mail(subject, message, from_email,
                          recipient_list, fail_silently=fail_silently,
                          auth_user=auth_user, auth_password=auth_password,
                          connection=connection, html_message=html_message)


def html_from_plaintext(plaintext):
    """
    Convert a plaintext message to html by rendering it as markdown.  We add
    extra newlines so that markdown inserts the appropriate <p> tags
    """
    return markdown(plaintext.replace('\n', '\n\n'))


def _can_email(communication_type, email):
    """
        Try to get the Worker associated with the given email and query if they
        want to receive a message for the given communication_type.
    """
    try:
        worker = Worker.objects.get(user__email=email)
        comm_pref = CommunicationPreference.objects.get(
            worker=worker,
            communication_type=communication_type
        )
        return comm_pref.can_email()
    except Worker.DoesNotExist:
        return True
