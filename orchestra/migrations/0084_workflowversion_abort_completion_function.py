# Generated by Django 2.2.9 on 2020-04-09 14:27

from django.db import migrations
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0083_update_staffbot_request_status_choices'),
    ]

    operations = [
        migrations.AddField(
            model_name='workflowversion',
            name='abort_completion_function',
            field=jsonfield.fields.JSONField(default={}),
        ),
    ]
