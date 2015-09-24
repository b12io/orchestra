from django.dispatch import receiver
from registration.signals import user_registered

from orchestra.models import Worker


@receiver(user_registered)
def add_worker_for_new_users(sender, user, request, **kwargs):
    Worker.objects.create(user=user)
