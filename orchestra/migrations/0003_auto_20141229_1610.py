# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0002_auto_20141229_1543'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='short_description',
            field=models.CharField(default='', max_length=100),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='project',
            name='task_class',
            field=models.IntegerField(
                choices=[(0, 'Training tasks'), (1, 'A real task')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='step',
            name='worker_type',
            field=models.IntegerField(choices=[(0, 'Human'), (1, 'Machine')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='task',
            name='status',
            field=models.IntegerField(choices=[(0, 'Awaiting Processing'), (1, 'Processing'), (
                2, 'Pending Review'), (3, 'Reviewing'), (4, 'Post-review Processing'), (5, 'Complete')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='taskassignment',
            name='status',
            field=models.IntegerField(
                choices=[(0, 'Procesing'), (1, 'Submitted')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='workercertification',
            name='role',
            field=models.IntegerField(
                choices=[(0, 'Entry-level'), (1, 'Reviewer')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='workercertification',
            name='task_class',
            field=models.IntegerField(
                choices=[(0, 'Training tasks'), (1, 'A real task')]),
            preserve_default=True,
        ),
    ]
