from django.contrib.auth.models import User
from django.contrib.auth.models import Group

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
            'email': 'noreply-simple1@example.org'
        }
    )
    user.set_password('demo')
    user.save()
    if created:
        Worker.objects.create(user=user)
    project_admins, created = Group.objects.get_or_create(
        name='project_admins')
    if created:
        user.groups.add(project_admins)
