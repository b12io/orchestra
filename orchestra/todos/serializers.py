from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from django.db import IntegrityError

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


class TodoBulkCreateListSerializer(serializers.ListSerializer):
    def create(self, validated_data):
        result = [self.child.create(attrs) for attrs in validated_data]
        try:
            self.child.Meta.model.objects.bulk_create(result)
        except IntegrityError as e:
            raise ValidationError(e)
        return result

    def update(self, instances, validated_data):
        result = []
        for instance, data in zip(instances, validated_data):
            result.append(self.child.update(instance, data))

        writable_fields = [
            x for x in self.child.Meta.fields
            if x not in self.child.Meta.read_only_fields
        ]

        try:
            self.child.Meta.model.objects.bulk_update(result, writable_fields)
        except IntegrityError as e:
            raise ValidationError(e)

        return result


class BulkTodoSerializer(serializers.ModelSerializer):
    json_schemas = {
        'activity_log': TodoActionListSchema
    }

    # TODO(murat): Remove this validation when step will be marked as required
    def validate(self, data):
        if 'step' not in data.keys():
            raise serializers.ValidationError(
                {'step': ['step should be supplied.']}
            )
        if 'project' not in data.keys():
            raise serializers.ValidationError(
                {'project': ['project should be supplied.']}
            )
        return data

    def create(self, validated_data):
        instance = Todo(**validated_data)
        if isinstance(self._kwargs['data'], dict):
            instance.save()
        return instance

    def update(self, instance, validated_data):
        for k, v in validated_data.items():
            setattr(instance, k, v)

        if isinstance(self._kwargs['data'], dict):
            instance.save()
        return instance

    class Meta:
        model = Todo
        fields = (
            'id',
            'created_at',
            'task',
            'title',
            'parent_todo',
            'template',
            'completed',
            'skipped_datetime',
            'start_by_datetime',
            'due_datetime',
            'activity_log',
            'section',
            'project',
            'step',
            'order',
            'status',
            'additional_data')
        read_only_fields = ('id',)
        list_serializer_class = TodoBulkCreateListSerializer


class BulkTodoSerializerWithoutQA(BulkTodoSerializer):
    qa = serializers.SerializerMethodField()

    def get_qa(self, obj):
        return None

    class Meta(BulkTodoSerializer.Meta):
        fields = BulkTodoSerializer.Meta.fields + ('qa',)


class BulkTodoSerializerWithQA(BulkTodoSerializer):
    qa = TodoQASerializer(read_only=True)

    class Meta(BulkTodoSerializer.Meta):
        fields = BulkTodoSerializer.Meta.fields + ('qa',)
