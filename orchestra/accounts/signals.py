from django.dispatch import receiver
from django.dispatch import Signal

from orchestra.models import Worker
from orchestra.models import CommunicationPreference

# A user has activated his or her account.
orchestra_user_registered = Signal(providing_args=['user', 'request'])


@receiver(orchestra_user_registered)
def add_worker_for_new_users(sender, user, request, **kwargs):
    worker = Worker.objects.create(user=user)
    default_methods = CommunicationPreference.get_default_methods()
    choices = CommunicationPreference.CommunicationType.choices()
    for communication_type, _ in choices:
        CommunicationPreference.objects.create(
            worker=worker,
            methods=default_methods,
            communication_type=communication_type
        )
