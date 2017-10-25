# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import jsonfield.fields
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='project',
            field=models.ForeignKey(
                on_delete=models.CASCADE, default=0, to='orchestra.Project'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='process',
            name='description',
            field=models.TextField(blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='step',
            name='depends_on',
            field=models.ManyToManyField(
                related_name='depends_on_rel_+', to='orchestra.Step', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='step',
            name='description',
            field=models.TextField(blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='step',
            name='required_certifications',
            field=models.ManyToManyField(
                to='orchestra.Certification', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='step',
            name='review_policy',
            field=jsonfield.fields.JSONField(blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='step',
            name='user_interface',
            field=jsonfield.fields.JSONField(blank=True),
            preserve_default=True,
        ),
    ]
