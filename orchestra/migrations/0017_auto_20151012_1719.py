# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.utils.timezone
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0016_auto_20150819_1900'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='start_datetime',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
