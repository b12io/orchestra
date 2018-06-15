"""
Validation function for json schemas
"""
from jsonschema import Draft4Validator
from jsonschema import validators


def extend_with_default(validator_class):
    """
    Extends json schema validator so that it fills in default values.

    NOTE(aditya): Copied code from
    https://github.com/b12io/crowdsurfing/blob/master/product/common/json_schema.py
    """
    validate_properties = validator_class.VALIDATORS['properties']

    def set_defaults(validator, properties, instance, schema):
        for property, subschema in properties.items():
            if 'default' in subschema:
                instance.setdefault(property, subschema['default'])

        for error in validate_properties(
                validator, properties, instance, schema):
            yield error

    return validators.extend(validator_class, {'properties': set_defaults})


DefaultValidatingDraft4Validator = extend_with_default(Draft4Validator)
