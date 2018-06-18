from rest_framework import serializers

from orchestra.models import Todo
from orchestra.json_schemas.todos import TodoListSchema
from orchestra.utils.mixins import JSONSchemaValidationMixin


class TodoSerializer(serializers.ModelSerializer, JSONSchemaValidationMixin):
    json_schemas = {
        'items': TodoListSchema
    }

    class Meta:
        model = Todo
        fields = (
            'id',
            'created_at',
            'task',
            'description',
            'completed',
            'skipped_datetime',
            'start_by_datetime',
            'due_datetime')
        read_only_fields = ('id',)
