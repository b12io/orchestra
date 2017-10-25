# -*- coding: utf-8 -*-
# Manually written
from __future__ import unicode_literals

import logging

from django.db import connection
from django.db import migrations
from django.db import models

logger = logging.getLogger(__name__)


def delete_timeentries_marked_for_delete(apps, schema_editor):
    TimeEntry = apps.get_model('orchestra', 'TimeEntry')
    TimeEntry.objects.filter(is_deleted=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0050_auto_20160428_1751'),
    ]

    operations = [
        migrations.RunPython(delete_timeentries_marked_for_delete),  # manually-reviewed
    ]
