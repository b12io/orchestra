# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def set_task_start_datetime(apps, schema_editor):
    """Fill in legacy `Task.start_datetime` as `Project.start_datetime.`"""
    Task = apps.get_model('orchestra', 'Task')  # noqa
    for task in Task.objects.all():
        task.start_datetime = task.project.start_datetime
        task.save()


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0017_auto_20151012_1719'),
    ]

    operations = [
        migrations.RunPython(set_task_start_datetime),  # manually-reviewed
    ]
