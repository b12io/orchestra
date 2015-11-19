from django.contrib.auth.models import User
from orchestra.models import Certification
from orchestra.models import Worker
from orchestra.models import WorkerCertification


def load(workflow_version):
    """ Loads workers for running the journalism workflow. """
    for user_data in USERS:
        # Create the user/worker objects and set the password.
        username = user_data.pop('username')
        password = user_data.pop('password')
        certifications = user_data.pop('certifications')
        user, _ = User.objects.update_or_create(
            username=username,
            defaults=user_data,
        )
        user.set_password(password)
        user.save()
        worker, _ = Worker.objects.update_or_create(user=user)

        # Grant the worker the desired certifications.
        for certification_slug, certification_role in certifications:
            certification = Certification.objects.get(
                slug=certification_slug)
            WorkerCertification.objects.update_or_create(
                certification=certification,
                worker=worker,
                task_class=WorkerCertification.TaskClass.REAL,
                role=certification_role)

USERS = [
    {
        'username': 'journalism-editor',
        'first_name': 'Journalism',
        'last_name': 'Editor',
        'is_active': True,
        'is_superuser': False,
        'is_staff': False,
        'email': 'noreply@example.org',
        'password': 'editor',
        'certifications': [
            ('editor', WorkerCertification.Role.ENTRY_LEVEL),
        ]
    },
    {
        'username': 'journalism-reporter-1',
        'first_name': 'Journalism',
        'last_name': 'Reporter1',
        'is_active': True,
        'is_superuser': False,
        'is_staff': False,
        'password': 'reporter',
        'email': 'noreply@example.org',
        'certifications': [
            ('reporter', WorkerCertification.Role.ENTRY_LEVEL),
        ]
    },
    {
        'username': 'journalism-reporter-2',
        'first_name': 'Journalism',
        'last_name': 'Reporter2',
        'is_active': True,
        'is_superuser': False,
        'is_staff': False,
        'password': 'reporter',
        'email': 'noreply@example.org',
        'certifications': [
            ('reporter', WorkerCertification.Role.ENTRY_LEVEL),
            ('reporter', WorkerCertification.Role.REVIEWER),
        ],
    },
    {
        'username': 'journalism-photographer-1',
        'first_name': 'Journalism',
        'last_name': 'Photographer1',
        'is_active': True,
        'is_superuser': False,
        'is_staff': False,
        'password': 'photographer',
        'email': 'noreply@example.org',
        'certifications': [
            ('photographer', WorkerCertification.Role.ENTRY_LEVEL),
        ]
    },
    {
        'username': 'journalism-photographer-2',
        'first_name': 'Journalism',
        'last_name': 'Photographer2',
        'is_active': True,
        'is_superuser': False,
        'is_staff': False,
        'password': 'photographer',
        'email': 'noreply@example.org',
        'certifications': [
            ('photographer', WorkerCertification.Role.ENTRY_LEVEL),
            ('photographer', WorkerCertification.Role.REVIEWER),
        ]
    },
    {
        'username': 'journalism-copy-editor',
        'first_name': 'Journalism',
        'last_name': 'CopyEditor',
        'is_active': True,
        'is_superuser': False,
        'is_staff': False,
        'password': 'copy-editor',
        'email': 'noreply@example.org',
        'certifications': [
            ('copy_editor', WorkerCertification.Role.ENTRY_LEVEL),
        ]
    },
]
