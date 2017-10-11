# -*- coding: utf-8 -*-
"""
Links existing projects and tasks to the new workflow database entries.

**This migration assumes that the new workflows are already in the database.**
One possible path for achieving this is to run:

* `python manage.py migrate orchestra 0017`, to get the DB up to the previous
  migration.

* `python manage.py loadworkflow /path/to/workflow version_slug` for all
  existing workflow versions, to ensure that they are all in the DB.

* `python manage.py migrate orchestra`, to run this migration and subsequent
  ones.
"""
from __future__ import unicode_literals

from django.db import migrations
from django.db import models


def update_projects(apps, schema_editor):
    Project = apps.get_model('orchestra', 'Project')
    WorkflowVersion = apps.get_model('orchestra', 'WorkflowVersion')

    for project in Project.objects.all():
        project.workflow_version = WorkflowVersion.objects.get(
            slug=project.workflow_slug)
        project.save()


def update_tasks(apps, schema_editor):
    Task = apps.get_model('orchestra', 'Task')
    Step = apps.get_model('orchestra', 'Step')

    for task in Task.objects.all():
        task.step = Step.objects.get(slug=task.step_slug)
        task.save()


def migrate_worker_certifications(apps, schema_editor):
    Certification = apps.get_model('orchestra', 'Certification')
    WorkerCertification = apps.get_model('orchestra', 'WorkerCertification')

    # Copy unscoped worker certifications to the new scoped objects.
    unscoped_worker_certifications = WorkerCertification.objects.filter(
        certification__workflow__isnull=True,
    )
    for worker_certification in unscoped_worker_certifications:
        scoped_certifications = Certification.objects.filter(
            workflow__isnull=False,
            slug=worker_certification.certification.slug,
        )

        # Since unscoped certifications are 'global', create a new
        # WorkerCertification for all new scoped certifications.
        for certification in scoped_certifications:
            WorkerCertification.objects.create(
                certification=certification,
                worker=worker_certification.worker,
                task_class=worker_certification.task_class,
                role=worker_certification.role
            )

        # Delete worker certs we successfully copied.
        # Necessary so we can make Certification.workflow non-nullable.
        if scoped_certifications.exists():
            worker_certification.delete()

    # Verify that we've migrated all unscoped worker certifications
    unmigrated_certifications = (Certification.objects
                                 .exclude(workercertification=None)
                                 .filter(workflow__isnull=True))
    if unmigrated_certifications.exists():
        raise ValueError('Failed to migrate all worker certifications!')

    # Delete unscoped certifications.
    # Necessary so we can make Certification.workflow non-nullable.
    Certification.objects.filter(workflow__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0017_auto_20151007_1424'),
    ]

    # TODO(dhaas): Write reverse migrations for these.
    operations = [
        migrations.RunPython(update_projects, migrations.RunPython.noop), # manually-reviewed
        migrations.RunPython(update_tasks, migrations.RunPython.noop), # manually-reviewed
        migrations.RunPython(migrate_worker_certifications,  # manually-reviewed
                             migrations.RunPython.noop),  # manually-reviewed
    ]
