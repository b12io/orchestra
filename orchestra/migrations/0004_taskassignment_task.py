# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0003_auto_20141229_1610'),
    ]

    operations = [
        migrations.AddField(
            model_name='taskassignment',
            name='task',
            field=models.ForeignKey(default=0, to='orchestra.Task'),
            preserve_default=False,
        ),
    ]
