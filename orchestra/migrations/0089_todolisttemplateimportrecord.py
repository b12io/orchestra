# Generated by Django 2.2.13 on 2020-09-20 15:59

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import orchestra.models.core.mixins
import orchestra.utils.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('orchestra', '0088_change_related_name_todos_old'),
    ]

    operations = [
        migrations.CreateModel(
            name='TodoListTemplateImportRecord',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('is_deleted', models.BooleanField(default=False)),
                ('import_url', models.URLField(blank=True, null=True)),
                ('importer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('todo_list_template', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='orchestra.TodoListTemplate')),
            ],
            bases=(orchestra.models.core.mixins.TodoListTemplateImportRecordMixin, orchestra.utils.models.DeleteMixin, models.Model),
        ),
    ]