# -*- coding: utf-8 -*-
# Manually written
from __future__ import unicode_literals

from django.db import connection, migrations, models

import logging

logger = logging.getLogger(__name__)


def delete_timeentries_marked_for_delete(apps, schema_editor):
    cursor = connection.cursor()
    cursor.execute('DELETE FROM orchestra_timeentry where is_deleted=true')
    print('Deleted {} rows'.format(cursor.rowcount))
    cursor.close()


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0044_auto_20160426_0044'),
    ]

    operations = [
        migrations.RunPython(delete_timeentries_marked_for_delete),  # manually-reviewed
    ]
