# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0008_auto_20150520_1953'),
    ]

    operations = [
        migrations.AlterField(
            model_name='certification',
            name='required_certifications',
            field=models.ManyToManyField(
                blank=True, to='orchestra.Certification', related_name='required_certifications_rel_+'),
        ),
        migrations.AlterField(
            model_name='task',
            name='step_slug',
            field=models.CharField(max_length=200, choices=[
                                   ('content_extraction', ' Content Extraction'), ('copy_pass', 'Copy Pass')]),
        ),
        migrations.AlterField(
            model_name='worker',
            name='user',
            field=models.OneToOneField(on_delete=models.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]
