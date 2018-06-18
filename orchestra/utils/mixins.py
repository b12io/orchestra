from orchestra.json_schemas.validation import validate_json


class JSONSchemaValidationMixin(object):
    json_schemas = {}

    def save(self, *args, **kwargs):
        for blob_key, json_schema in self.json_schemas.items():
            validate_json(blob_key, json_schema,
                          getattr(self, blob_key, None))
        super().save(*args, **kwargs)
