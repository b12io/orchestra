# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0011_auto_20150618_0003'),
    ]

    operations = [
        migrations.AlterField(
            model_name='project',
            name='process_slug',
            field=models.CharField(max_length=200, choices=[(
                'website_design', 'Website design'), ('website_enhancement', 'Website enhancement')]),
        ),
        migrations.AlterField(
            model_name='project',
            name='short_description',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='task',
            name='step_slug',
            field=models.CharField(max_length=200, choices=[('design', 'Design'), ('export', 'Export design'), (
                'website_enhancement', 'Enhance'), ('export_enhancement_step', 'Export enhancement')]),
        ),
    ]
