# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.utils.timezone
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0019_auto_20151022_1531'),
    ]

    operations = [
        migrations.AlterField(
            model_name='project',
            name='start_datetime',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
