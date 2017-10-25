# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0003_auto_20141229_1610'),
    ]

    operations = [
        migrations.AddField(
            model_name='taskassignment',
            name='task',
            field=models.ForeignKey(
                on_delete=models.CASCADE, default=0, to='orchestra.Task'),
            preserve_default=False,
        ),
    ]
