# -*- coding: utf-8 -*-
# Manually written
from __future__ import unicode_literals

from django.db import migrations, models

import datetime
import dateutil


def create_time_entries(apps, schema_editor):
    TaskAssignment = apps.get_model('orchestra', 'TaskAssignment')
    TimeEntry = apps.get_model('orchestra', 'TimeEntry')

    for assignment in TaskAssignment.objects.all():
        # Check if keys exist before processing, to be compatible with previous
        # versions of snapshots.
        if 'snapshots' not in assignment.snapshots:
            continue
        for snapshot in assignment.snapshots['snapshots']:
            if 'datetime' not in snapshot or 'work_time_seconds' not in snapshot:
                continue
            date = dateutil.parser.parse(snapshot['datetime']).date()
            time_worked = datetime.timedelta(seconds=snapshot['work_time_seconds'])
            TimeEntry.objects.get_or_create(assignment=assignment, date=date,
                                            time_worked=time_worked)


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0034_timeentry_is_deleted'),
    ]

    operations = [
        migrations.RunPython(create_time_entries),  # manually-reviewed
    ]
