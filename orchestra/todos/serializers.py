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
            'title',
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
            'title',
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


class TodoBulkCreateListSerializer(serializers.ListSerializer):
    def create(self, validated_data):
        result = [self.child.create(attrs) for attrs in validated_data]
        try:
            self.child.Meta.model.objects.bulk_create(result)
        except IntegrityError as e:
            raise ValidationError(e)
        return result

    def update(self, instances, validated_data):
        instance_hash = {
            index: instance for index, instance in enumerate(instances)}

        result = [
            self.child.update(instance_hash[index], attrs)
            for index, attrs in enumerate(validated_data)
        ]

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
            'id', 'title', 'details', 'section', 'project', 'step',
            'order', 'completed', 'start_by_datetime', 'due_datetime',
            'skipped_datetime', 'parent_todo', 'template', 'activity_log',
            'status', 'additional_data')
        read_only_fields = ('id',)
        list_serializer_class = TodoBulkCreateListSerializer
