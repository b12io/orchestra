# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.utils.timezone
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0023_assignment_failed'),
    ]

    operations = [
        migrations.AddField(
            model_name='certification',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='step',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='workercertification',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='workflow',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='workflowversion',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
