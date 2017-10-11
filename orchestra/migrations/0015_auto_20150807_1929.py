# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0014_auto_20150717_2015'),
    ]

    operations = [
        migrations.AlterField(
            model_name='project',
            name='status',
            field=models.IntegerField(
                default=0, choices=[(0, 'Active'), (2, 'Aborted')]),
        ),
        migrations.AlterField(
            model_name='task',
            name='status',
            field=models.IntegerField(choices=[(0, 'Awaiting Processing'), (1, 'Processing'), (2, 'Pending Review'), (
                3, 'Reviewing'), (4, 'Post-review Processing'), (6, 'Aborted'), (5, 'Complete')]),
        ),
        migrations.AlterField(
            model_name='task',
            name='step_slug',
            field=models.CharField(choices=[('media_extraction', 'Media Extraction'), ('design', 'Design'), ('export', 'Export design'), (
                'export_enhancement_step', 'Export enhancement'), ('website_enhancement', 'Enhance')], max_length=200),
        ),
        migrations.AlterField(
            model_name='workercertification',
            name='worker',
            field=models.ForeignKey(
                on_delete=models.CASCADE,
                to='orchestra.Worker', related_name='certifications'),
        ),
        migrations.AlterUniqueTogether(  # manually-reviewed
            name='workercertification',
            unique_together=set(
                [('certification', 'worker', 'task_class', 'role')]),
        ),
    ]
