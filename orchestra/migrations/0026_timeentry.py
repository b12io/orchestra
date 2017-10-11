# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-04-05 19:27
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0025_iteration'),
    ]

    operations = [
        migrations.CreateModel(
            name='TimeEntry',
            fields=[
                ('id', models.AutoField(auto_created=True,
                                        primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('time_worked', models.DurationField()),
                ('description', models.CharField(
                    blank=True, max_length=200, null=True)),
                ('assignment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                 related_name='time_entries', to='orchestra.TaskAssignment')),
            ],
        ),
    ]
