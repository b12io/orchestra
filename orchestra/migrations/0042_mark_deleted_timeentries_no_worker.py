# -*- coding: utf-8 -*-
# Manually written
from __future__ import unicode_literals

from django.db import migrations, models

import logging

logger = logging.getLogger(__name__)


def fill_in_worker_on_time_entries_or_delete(apps, schema_editor):
    TimeEntry = apps.get_model('orchestra', 'TimeEntry')

    for time_entry in TimeEntry.objects.all():
        if (time_entry.assignment is None or
            time_entry.assignment.worker is None):
            # Mark time entry as deleted.
            print('Deleting Time Entry {} ({} hours worked) because'.format(
                time_entry.id, time_entry.time_worked),
                  'TaskAssignment {} is None or has no worker'.format(
                      time_entry.assignment))
            time_entry.is_deleted = True
            time_entry.save()
        else:
            time_entry.worker = time_entry.assignment.worker
            time_entry.save()


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0041_alter_payrate_fields'),
    ]

    operations = [
        migrations.RunPython(fill_in_worker_on_time_entries_or_delete),  # manually-reviewed
    ]
