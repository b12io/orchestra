# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-04-15 18:39
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0039_copy_start_datetime_to_created_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='timeentry',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
