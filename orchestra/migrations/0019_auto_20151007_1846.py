# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0018_auto_20151007_1451'),
    ]

    operations = [
        migrations.RemoveField(  # manually-reviewed
            model_name='project',
            name='workflow_slug',
        ),
        migrations.RemoveField(  # manually-reviewed
            model_name='task',
            name='step_slug',
        ),
        migrations.AlterField(
            model_name='certification',
            name='workflow',
            field=models.ForeignKey(to='orchestra.Workflow', related_name='certifications'),
        ),
        migrations.AlterField(
            model_name='project',
            name='workflow_version',
            field=models.ForeignKey(to='orchestra.WorkflowVersion', related_name='projects'),
        ),
        migrations.AlterField(
            model_name='task',
            name='step',
            field=models.ForeignKey(to='orchestra.Step', related_name='tasks'),
        ),
        migrations.AlterField(
            model_name='step',
            name='workflow_version',
            field=models.ForeignKey(to='orchestra.WorkflowVersion', related_name='steps'),
        ),
        migrations.AlterField(
            model_name='workflowversion',
            name='workflow',
            field=models.ForeignKey(to='orchestra.Workflow', related_name='versions'),
        ),
    ]
