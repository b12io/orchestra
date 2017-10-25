# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0010_merge'),
    ]

    operations = [
        migrations.AlterField(
            model_name='project',
            name='process_slug',
            field=models.CharField(max_length=200, choices=[('website_enhancement_experiment', 'Website Enhancement Experiment'), (
                'website_enhancement', 'Website Enhancement'), ('doctors', 'Doctors Process')]),
        ),
        migrations.AlterField(
            model_name='task',
            name='step_slug',
            field=models.CharField(max_length=200, choices=[('website_enhancement_experiment', 'Website Enhancement'), (
                'website_enhancement', 'Website Enhancement'), ('export', 'Export'), ('design', 'Design'), ('content_extraction', ' Content Extraction')]),
        ),
        migrations.AlterField(
            model_name='taskassignment',
            name='status',
            field=models.IntegerField(
                choices=[(0, 'Processing'), (1, 'Submitted')]),
        ),
        migrations.AlterField(
            model_name='taskassignment',
            name='worker',
            field=models.ForeignKey(
                on_delete=models.CASCADE, blank=True, null=True, to='orchestra.Worker'),
        ),
    ]
