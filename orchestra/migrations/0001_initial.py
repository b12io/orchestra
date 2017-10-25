# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import jsonfield.fields
from django.conf import settings
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Certification',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('slug', models.CharField(unique=True, max_length=200)),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('required_certifications', models.ManyToManyField(
                    related_name='required_certifications_rel_+', to='orchestra.Certification')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Process',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('slug', models.CharField(unique=True, max_length=200)),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('start_datetime', models.DateTimeField(auto_now_add=True)),
                ('priority', models.IntegerField()),
                ('task_class', models.IntegerField(
                    choices=[(0, b'Training tasks'), (1, b'A real task')])),
                ('process', models.ForeignKey(
                    on_delete=models.CASCADE, to='orchestra.Process')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Step',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('slug', models.CharField(max_length=200)),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('worker_type', models.IntegerField(
                    choices=[(0, b'Human'), (1, b'Machine')])),
                ('review_policy', jsonfield.fields.JSONField()),
                ('user_interface', jsonfield.fields.JSONField()),
                ('depends_on', models.ManyToManyField(
                    related_name='depends_on_rel_+', to='orchestra.Step')),
                ('process', models.ForeignKey(
                    on_delete=models.CASCADE, to='orchestra.Process')),
                ('required_certifications', models.ManyToManyField(
                    to='orchestra.Certification')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', models.IntegerField(choices=[(0, b'Awaiting Processing'), (1, b'Processing'), (
                    2, b'Pending Review'), (3, b'Reviewing'), (4, b'Post-review Processing'), (5, b'Complete')])),
                ('step', models.ForeignKey(
                    on_delete=models.CASCADE, to='orchestra.Step')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TaskAssignment',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('start_datetime', models.DateTimeField(auto_now_add=True)),
                ('status', models.IntegerField(
                    choices=[(0, b'Procesing'), (1, b'Submitted')])),
                ('in_progress_task_data', jsonfield.fields.JSONField()),
                ('snapshots', jsonfield.fields.JSONField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Worker',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('start_datetime', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(
                    on_delete=models.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='WorkerCertification',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('task_class', models.IntegerField(
                    choices=[(0, b'Training tasks'), (1, b'A real task')])),
                ('role', models.IntegerField(
                    choices=[(0, b'Entry-level'), (1, b'Reviewer')])),
                ('certification', models.ForeignKey(on_delete=models.CASCADE,
                                                    to='orchestra.Certification')),
                ('worker', models.ForeignKey(
                    on_delete=models.CASCADE, to='orchestra.Worker')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='taskassignment',
            name='worker',
            field=models.ForeignKey(
                on_delete=models.CASCADE, to='orchestra.Worker'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(  # manually-reviewed
            name='step',
            unique_together=set([('process', 'slug')]),
        ),
    ]
