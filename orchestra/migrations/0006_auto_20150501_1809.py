# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('orchestra', '0005_auto_20150402_0538'),
    ]

    operations = [
        migrations.RenameField(
            model_name='task',
            old_name='step',
            new_name='step_slug'
        ),
        migrations.RenameField(
            model_name='project',
            old_name='process',
            new_name='process_slug'
        ),
    ]
