# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0012_auto_20150701_1948'),
    ]

    operations = [
        migrations.RenameField(
            model_name='Project',
            old_name='process_slug',
            new_name='workflow_slug',
        ),
    ]
