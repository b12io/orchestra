# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2018-01-10 20:01
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0073_remove_worker_staffing_priority'),
    ]

    operations = [
        migrations.AddField(
            model_name='todo',
            name='due_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='todo',
            name='start_date',
            field=models.DateField(default=django.utils.timezone.now),
        ),
    ]
