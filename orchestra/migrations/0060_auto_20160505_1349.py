# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-05-05 13:49
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0059_step_description_function'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='StaffingRequest',
            new_name='StaffingRequestInquiry',
        ),
    ]
