# Generated by Django 2.2.9 on 2020-03-30 19:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra', '0082_task_tags'),
    ]

    operations = [
        migrations.AlterField(
            model_name='staffbotrequest',
            name='status',
            field=models.IntegerField(choices=[(0, 'sending inquiries'), (1, 'done sending inquiries'), (2, 'complete')], default=0),
        ),
    ]
