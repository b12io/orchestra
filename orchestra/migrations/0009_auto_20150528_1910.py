# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0008_auto_20150520_1953'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='review_document_url',
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='task',
            name='step_slug',
            field=models.CharField(choices=[(
                'content_extraction', ' Content Extraction'), ('copy_pass', 'Copy Pass')], max_length=200),
        ),
    ]
