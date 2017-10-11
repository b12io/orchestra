# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0022_auto_20151217_1642'),
    ]

    operations = [
        migrations.AlterField(
            model_name='taskassignment',
            name='status',
            field=models.IntegerField(choices=[(0, 'Processing'), (1, 'Submitted'), (2, 'Failed')]),
        ),
    ]
