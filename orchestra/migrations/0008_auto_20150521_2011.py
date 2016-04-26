# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0007_auto_20150507_0204'),
    ]

    operations = [
        migrations.AlterField(
            model_name='certification',
            name='required_certifications',
            field=models.ManyToManyField(
                related_name='required_certifications_rel_+', to='orchestra.Certification'),
        ),
        migrations.AlterUniqueTogether(  # manually-reviewed
            name='taskassignment',
            unique_together=set([('task', 'assignment_counter')]),
        ),
    ]
