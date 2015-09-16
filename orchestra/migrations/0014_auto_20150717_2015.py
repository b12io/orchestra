# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0013_auto_20150707_0054'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='status',
            field=models.IntegerField(default=0, choices=[(-1, 'Aborted'), (0, 'Active')]),
        ),
        migrations.AlterField(
            model_name='task',
            name='step_slug',
            field=models.CharField(choices=[('design', 'Design'), ('media_extraction', 'Media Extraction'), ('export', 'Export design'), ('export_enhancement_step', 'Export enhancement'), ('website_enhancement', 'Enhance')], max_length=200),
        ),
    ]
