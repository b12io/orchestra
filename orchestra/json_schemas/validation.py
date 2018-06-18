from orchestra.utils.json_schema import DefaultValidatingDraft4Validator


def validate_json(blob_key, json_schema, data):
    """
    Validate json blobs against their json schema.
    :param blob_key: key name for data in model
    :param json_schema: JSON schema object
    :param data: JSON data, defaults are added to it.
    """
    if not data:
        # Don't validate when data is empty. Otherwise, won't be able to
        # create empty database objects.
        return data
    schema = json_schema.get_schema()
    DefaultValidatingDraft4Validator(schema).validate(data)
    return data
