from rest_framework import serializers

from orchestra.models import Todo


class TodoSerializer(serializers.ModelSerializer):

    class Meta:
        model = Todo
        fields = ('id', 'created_at', 'task', 'description', 'completed', 'start_date', 'due_date')
        read_only_fields = ('id',)
