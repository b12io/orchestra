# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2018-01-03 02:21
from __future__ import unicode_literals

from django.db import migrations
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0074_sanitycheck'),
    ]

    operations = [
        migrations.AddField(
            model_name='workflowversion',
            name='sanity_checks',
            field=jsonfield.fields.JSONField(default={}),
        ),
    ]
