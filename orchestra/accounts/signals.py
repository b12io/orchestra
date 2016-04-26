from django.dispatch import receiver
from django.dispatch import Signal

from orchestra.models import Worker

# A user has activated his or her account.
orchestra_user_registered = Signal(providing_args=['user', 'request'])


@receiver(orchestra_user_registered)
def add_worker_for_new_users(sender, user, request, **kwargs):
    Worker.objects.create(user=user)
