from rest_framework import serializers

from orchestra.models import Todo
from orchestra.models import TodoListTemplate
from orchestra.json_schemas.todos import TodoListSchema
from orchestra.utils.mixins import JSONSchemaValidationMixin


class TodoSerializer(serializers.ModelSerializer):

    class Meta:
        model = Todo
        fields = (
            'id',
            'created_at',
            'task',
            'description',
            'parent_todo',
            'template',
            'completed',
            'skipped_datetime',
            'start_by_datetime',
            'due_datetime')
        read_only_fields = ('id',)


class TodoListTemplateSerializer(serializers.ModelSerializer):
    json_schemas = {
        'todos': TodoListSchema
    }

    class Meta:
        model = TodoListTemplate
        fields = (
            'id',
            'created_at',
            'slug',
            'name',
            'description',
            'creator',
            'todos')
        read_only_fields = ('id',)
