# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0018_auto_20151014_1432'),
    ]

    operations = [
        migrations.AlterField(
            model_name='taskassignment',
            name='in_progress_task_data',
            field=jsonfield.fields.JSONField(default={}),
        ),
        migrations.AlterField(
            model_name='taskassignment',
            name='snapshots',
            field=jsonfield.fields.JSONField(default={}),
        ),
    ]
