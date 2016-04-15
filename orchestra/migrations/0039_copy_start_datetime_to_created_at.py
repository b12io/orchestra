# -*- coding: utf-8 -*-
# Manually written
from __future__ import unicode_literals

from django.db import migrations


def copy_start_datetime_to_created_at(apps, schema_editor):
    Iteration = apps.get_model('orchestra', 'Iteration')
    TaskAssignment = apps.get_model('orchestra', 'TaskAssignment')

    for iteration in Iteration.objects.all():
        iteration.created_at = iteration.start_datetime
        iteration.save()

    for assignment in TaskAssignment.objects.all():
        assignment.created_at = assignment.start_datetime
        assignment.save()


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0038_add_fields_to_taskassignment'),
    ]

    operations = [
        migrations.RunPython(copy_start_datetime_to_created_at),  # manually-reviewed
    ]
