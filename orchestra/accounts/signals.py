from django.dispatch import receiver
from django.dispatch import Signal

from orchestra.models import Worker
from orchestra.models import CommunicationPreference

# A user has activated his or her account.
orchestra_user_registered = Signal(providing_args=['user', 'request'])


@receiver(orchestra_user_registered)
def add_worker_for_new_users(sender, user, request, **kwargs):
    worker, _ = Worker.objects.get_or_create(user=user)
    CommunicationPreference.objects.get_or_create_all_types(worker)
