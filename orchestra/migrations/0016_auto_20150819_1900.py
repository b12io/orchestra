# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0015_auto_20150807_1929'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='slack_group_id',
            field=models.CharField(null=True, blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='worker',
            name='slack_username',
            field=models.CharField(null=True, blank=True, max_length=200),
        ),
        migrations.AlterField(
            model_name='project',
            name='workflow_slug',
            field=models.CharField(max_length=200, choices=[('website_enhancement', 'Website enhancement'), (
                'website_design_v2', 'Website design v2'), ('website_design', 'Website design')]),
        ),
        migrations.AlterField(
            model_name='task',
            name='step_slug',
            field=models.CharField(max_length=200, choices=[('export_enhancement_step', 'Export enhancement'), ('website_enhancement', 'Enhance'), ('design_v2', 'Design'), ('client_interview_v2', 'Client Interview'), ('seo_v2', 'SEO Optimization'), (
                'communication_delivery_v2', 'Communication & Delivery'), ('export_v2', 'Export design'), ('media_extraction_v2', 'Media Extraction'), ('ramp_down_v2', 'Ramping Down'), ('ramp_up_v2', 'Ramping Up'), ('design', 'Design'), ('media_extraction', 'Media Extraction'), ('export', 'Export design')]),
        ),
    ]
