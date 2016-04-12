# -*- coding: utf-8 -*-
# Manually written
from __future__ import unicode_literals

from django.db import migrations, models

import logging

logger = logging.getLogger(__name__)


def fill_in_worker_on_time_entries(apps, schema_editor):
    TimeEntry = apps.get_model('orchestra', 'TimeEntry')

    for time_entry in TimeEntry.objects.all():
        if time_entry.assignment.worker is None:
            print('WARN: TaskAssignment {} has no worker'.format(
                time_entry.assignment.id))
        time_entry.worker = time_entry.assignment.worker
        time_entry.save()


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0030_tasktimer_and_timer_fields_on_timeentry'),
    ]

    operations = [
        migrations.RunPython(fill_in_worker_on_time_entries),  # manually-reviewed
    ]
