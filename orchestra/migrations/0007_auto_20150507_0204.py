# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0006_auto_20150501_1809'),
    ]

    operations = [
        migrations.AddField(
            model_name='taskassignment',
            name='assignment_counter',
            field=models.IntegerField(default=0),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='certification',
            name='required_certifications',
            field=models.ManyToManyField(
                to='orchestra.Certification', related_name='required_certifications_rel_+', blank=True, null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='project',
            name='process_slug',
            field=models.CharField(
                max_length=200, choices=[('doctors', 'Doctors Process')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='task',
            name='step_slug',
            field=models.CharField(max_length=200, choices=[
                                   ('content_extraction', ' Content Extraction'), ('copy_pass', 'Copy Pass')]),
            preserve_default=True,
        ),
    ]
