from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from jsonschema import Draft4Validator
from jsonschema.exceptions import ValidationError as SchemaValidationError
from django.utils.translation import gettext_lazy
from orchestra.utils.json_schema import DefaultValidatingDraft4Validator


class JSONField(JSONField):
    default_error_messages = {
        'schema_invalid': gettext_lazy(
            'Value failed schema validation: %(err)s'),
    }

    def __init__(self, schema=None, add_defaults=False, *args, **kwargs):
        self.schema = schema
        self.add_defaults = add_defaults
        if self.schema and not isinstance(self.schema, dict):
            raise ValueError('Schema must be a dict object.')
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        # Only include kwarg if it's not the default
        if self.schema:
            kwargs['schema'] = self.schema
        if self.add_defaults:
            kwargs['add_defaults'] = self.add_defaults
        return name, path, args, kwargs

    def get_prep_value(self, value):
        self._validate_with_schema(value)
        return super().get_prep_value(value)

    def _validate_with_schema(self, value):
        if value and self.schema:
            try:
                self._get_validator_class()(self.schema).validate(value)
            except SchemaValidationError as err:
                raise ValidationError(
                    self.error_messages['schema_invalid'],
                    code='schema_invalid',
                    params={'err': err},
                )

    def _get_validator_class(self):
        if self.add_defaults:
            return DefaultValidatingDraft4Validator
        else:
            return Draft4Validator
