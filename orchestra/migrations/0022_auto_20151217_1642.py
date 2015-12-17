# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0021_merge'),
    ]

    operations = [
        migrations.RenameField(
            model_name='project',
            old_name='review_document_url',
            new_name='team_messages_url',
        ),
        migrations.AlterField(
            model_name='project',
            name='project_data',
            field=jsonfield.fields.JSONField(blank=True, default={}),
        ),
        migrations.AlterField(
            model_name='taskassignment',
            name='in_progress_task_data',
            field=jsonfield.fields.JSONField(blank=True, default={}),
        ),
        migrations.AlterField(
            model_name='taskassignment',
            name='snapshots',
            field=jsonfield.fields.JSONField(blank=True, default={}),
        ),
    ]
