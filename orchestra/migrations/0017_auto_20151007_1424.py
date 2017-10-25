# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import jsonfield.fields
from django.db import migrations
from django.db import models
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0016_auto_20150819_1900'),
    ]

    operations = [
        migrations.CreateModel(
            name='Workflow',
            fields=[
                ('id', models.AutoField(serialize=False,
                                        primary_key=True, verbose_name='ID', auto_created=True)),
                ('slug', models.CharField(max_length=200, unique=True)),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('code_directory', models.CharField(max_length=255, unique=True)),
                ('sample_data_load_function', jsonfield.fields.JSONField(default={})),
            ],
        ),
        migrations.CreateModel(
            name='Step',
            fields=[
                ('id', models.AutoField(serialize=False,
                                        primary_key=True, verbose_name='ID', auto_created=True)),
                ('slug', models.CharField(max_length=200)),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('is_human', models.BooleanField()),
                ('execution_function', jsonfield.fields.JSONField()),
                ('assignment_policy', jsonfield.fields.JSONField()),
                ('review_policy', jsonfield.fields.JSONField()),
                ('user_interface', jsonfield.fields.JSONField()),
                ('creation_depends_on', models.ManyToManyField(
                    to='orchestra.Step', related_name='creation_dependents', blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='WorkflowVersion',
            fields=[
                ('id', models.AutoField(serialize=False,
                                        primary_key=True, verbose_name='ID', auto_created=True)),
                ('slug', models.CharField(max_length=200)),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('workflow', models.ForeignKey(on_delete=models.CASCADE, null=True,
                                               to='orchestra.Workflow', related_name='versions')),
            ],
        ),
        migrations.AlterField(
            model_name='certification',
            name='slug',
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name='worker',
            name='start_datetime',
            field=models.DateTimeField(default=timezone.now),
        ),
        migrations.AddField(
            model_name='step',
            name='required_certifications',
            field=models.ManyToManyField(
                to='orchestra.Certification', blank=True),
        ),
        migrations.AddField(
            model_name='step',
            name='submission_depends_on',
            field=models.ManyToManyField(
                to='orchestra.Step', related_name='submission_dependents', blank=True),
        ),
        migrations.AddField(
            model_name='step',
            name='workflow_version',
            field=models.ForeignKey(on_delete=models.CASCADE,
                                    null=True, to='orchestra.WorkflowVersion', related_name='steps'),
        ),
        migrations.AddField(
            model_name='certification',
            name='workflow',
            field=models.ForeignKey(on_delete=models.CASCADE,
                                    null=True, to='orchestra.Workflow', related_name='certifications'),
        ),
        migrations.AlterField(
            model_name='certification',
            name='required_certifications',
            field=models.ManyToManyField(
                to='orchestra.Certification', blank=True, related_name='dependent_certifications'),
        ),
        migrations.AddField(
            model_name='project',
            name='workflow_version',
            field=models.ForeignKey(on_delete=models.CASCADE,
                                    null=True, to='orchestra.WorkflowVersion', related_name='projects'),
        ),
        migrations.AddField(
            model_name='task',
            name='step',
            field=models.ForeignKey(on_delete=models.CASCADE,
                                    null=True, to='orchestra.Step', related_name='tasks'),
        ),
        migrations.AlterUniqueTogether(  # manually-reviewed
            name='workflowversion',
            unique_together=set([('workflow', 'slug')]),
        ),
        migrations.AlterUniqueTogether(  # manually-reviewed
            name='step',
            unique_together=set([('workflow_version', 'slug')]),
        ),
        migrations.AlterUniqueTogether(  # manually-reviewed
            name='certification',
            unique_together=set([('workflow', 'slug')]),
        ),
    ]
