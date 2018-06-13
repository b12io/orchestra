from rest_framework import serializers

from orchestra.models import Todo
from orchestra.models import ChecklistTemplate


class TodoSerializer(serializers.ModelSerializer):

    class Meta:
        model = Todo
        fields = (
            'id',
            'created_at',
            'task',
            'description',
            'completed',
            'skipped',
            'start_by_datetime',
            'due_datetime')
        read_only_fields = ('id',)


class ChecklistTemplateSerializer(serializers.ModelSerializer):

    class Meta:
        model = ChecklistTemplate
        fields = (
            'id',
            'created_at',
            'slug',
            'name',
            'description',
            'creator',
            'todos')
        read_only_fields = ('id',)
