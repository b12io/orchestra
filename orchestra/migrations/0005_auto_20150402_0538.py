# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0004_taskassignment_task'),
    ]

    operations = [
        migrations.AlterUniqueTogether(  # manually-reviewed
            name='step',
            unique_together=None,
        ),
        migrations.RemoveField(  # manually-reviewed
            model_name='step',
            name='depends_on',
        ),
        migrations.RemoveField(  # manually-reviewed
            model_name='step',
            name='process',
        ),
        migrations.RemoveField(  # manually-reviewed
            model_name='step',
            name='required_certifications',
        ),
        migrations.AlterField(
            model_name='project',
            name='process',
            field=models.CharField(
                max_length=200, choices=[('Doctors', 'Doctors Process')]),
            preserve_default=True,
        ),
        migrations.DeleteModel(  # manually-reviewed
            name='Process',
        ),
        migrations.AlterField(
            model_name='task',
            name='project',
            field=models.ForeignKey(on_delete=models.CASCADE,
                                    related_name='tasks', to='orchestra.Project'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='task',
            name='step',
            field=models.CharField(max_length=200, choices=[
                                   ('Content Extraction', ' Content Extraction'), ('Copy Pass', ' Copy Pass')]),
            preserve_default=True,
        ),
        migrations.DeleteModel(  # manually-reviewed
            name='Step',
        ),
        migrations.AlterField(
            model_name='taskassignment',
            name='task',
            field=models.ForeignKey(on_delete=models.CASCADE,
                                    related_name='assignments', to='orchestra.Task'),
            preserve_default=True,
        ),
    ]
