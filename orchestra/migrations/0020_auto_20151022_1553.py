# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.utils.timezone
import jsonfield.fields
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0019_auto_20151007_1846'),
    ]

    operations = [
        migrations.AlterField(
            model_name='taskassignment',
            name='start_datetime',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='step',
            name='assignment_policy',
            field=jsonfield.fields.JSONField(default={}),
        ),
        migrations.AlterField(
            model_name='step',
            name='execution_function',
            field=jsonfield.fields.JSONField(default={}),
        ),
        migrations.AlterField(
            model_name='step',
            name='review_policy',
            field=jsonfield.fields.JSONField(default={}),
        ),
        migrations.AlterField(
            model_name='step',
            name='user_interface',
            field=jsonfield.fields.JSONField(default={}),
        ),
    ]
