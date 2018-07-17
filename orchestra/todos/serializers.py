from rest_framework import serializers

from orchestra.models import Todo
from orchestra.models import TodoQA
from orchestra.models import TodoListTemplate
from orchestra.json_schemas.todos import TodoListSchema
from orchestra.json_schemas.todos import TodoActionListSchema
from orchestra.utils.mixins import JSONSchemaValidationMixin


class TodoQASerializer(serializers.ModelSerializer):

    class Meta:
        model = TodoQA
        fields = (
            'id',
            'created_at',
            'todo',
            'approved',
            'comment')
        read_only_fields = ('id',)


class TodoSerializer(serializers.ModelSerializer):
    qa = serializers.SerializerMethodField()
    json_schemas = {
        'activity_log': TodoActionListSchema
    }

    def get_qa(self, obj):
        return None

    class Meta:
        model = Todo
        fields = (
            'id',
            'created_at',
            'task',
            'description',
            'parent_todo',
            'template',
            'qa',
            'completed',
            'skipped_datetime',
            'start_by_datetime',
            'due_datetime',
            'activity_log')
        read_only_fields = ('id',)


class TodoWithQASerializer(serializers.ModelSerializer):
    qa = TodoQASerializer(read_only=True)
    json_schemas = {
        'activity_log': TodoActionListSchema
    }

    class Meta:
        model = Todo
        fields = (
            'id',
            'created_at',
            'task',
            'description',
            'parent_todo',
            'template',
            'qa',
            'completed',
            'skipped_datetime',
            'start_by_datetime',
            'due_datetime',
            'activity_log')
        read_only_fields = ('id',)


class TodoListTemplateSerializer(serializers.ModelSerializer,
                                 JSONSchemaValidationMixin):
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
