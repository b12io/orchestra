from django.contrib.auth.models import User
from orchestra.models import Worker


def load(workflow_version):
    """ Loads a single worker for running the simple workflow. """
    user, created = User.objects.update_or_create(
        username='demo',
        defaults={
            'first_name': 'Demo',
            'last_name': 'User',
            'is_active': True,
            'is_superuser': False,
            'is_staff': False,
            'email': 'noreply@example.org'
        }
    )
    user.set_password('demo')
    user.save()
    if created:
        Worker.objects.create(user=user)
