from rest_framework import serializers

from orchestra.models import Todo


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
            'skipped_datetime',
            'start_by_datetime',
            'due_datetime')
        read_only_fields = ('id',)
