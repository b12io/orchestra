from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from django.db import IntegrityError

from orchestra.models import Todo
from orchestra.models import TodoQA
from orchestra.models import TodoListTemplate
from orchestra.json_schemas.todos import TodoListSchema
from orchestra.json_schemas.todos import TodoActionListSchema
from orchestra.utils.mixins import JSONSchemaValidationMixin
from orchestra.utils.common_helpers import get_step_by_project_id_and_step_slug


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


class StepField(serializers.Field):
    def to_representation(self, data):
        return data.slug

    def to_internal_value(self, value):
        return value


class BulkTodoSerializer(serializers.ModelSerializer):
    json_schemas = {
        'activity_log': TodoActionListSchema
    }

    step = StepField()
    additional_data = serializers.JSONField(required=False)

    # TODO(murat): Remove this validation when project
    # becomes a required field in models
    def validate(self, data):
        step = data.get('step')
        project = data.get('project')
        if step is not None and project is None:
            raise serializers.ValidationError({
                'project': [
                    'if step is given, project should also be supplied.']})
        return data

    def _set_step_to_validated_data(self, validated_data):
        project_id = validated_data['project'].id
        step = get_step_by_project_id_and_step_slug(project_id,
                                                    validated_data['step'])
        validated_data['step'] = step
        return validated_data

    def create(self, validated_data):
        validated_data = self._set_step_to_validated_data(validated_data)
        instance = Todo(**validated_data)
        if isinstance(self._kwargs['data'], dict):
            instance.save()
        return instance

    def update(self, instance, validated_data):
        if validated_data.get('step') is not None:
            validated_data = self._set_step_to_validated_data(validated_data)
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
            'title',
            'details',
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
            'additional_data',
            'is_deleted')
        read_only_fields = ('id',)
        list_serializer_class = TodoBulkCreateListSerializer


class BulkTodoSerializerWithoutQA(BulkTodoSerializer):
    qa = serializers.SerializerMethodField()

    def get_qa(self, obj):
        return None

    class Meta(BulkTodoSerializer.Meta):
        fields = BulkTodoSerializer.Meta.fields + ('qa',)
        read_only_fields = ('id',)


class BulkTodoSerializerWithQA(BulkTodoSerializer):
    qa = TodoQASerializer(read_only=True)

    class Meta(BulkTodoSerializer.Meta):
        fields = BulkTodoSerializer.Meta.fields + ('qa',)
        read_only_fields = ('id',)
