import jsl

TAG_STATUS = [
    'default',
    'primary',
    'success',
    'info',
    'warning',
    'danger',
]


class TagSchema(jsl.Document):
    """
    A tag schema

    Attributes:
        label (str):
            A text label of the tag
        status (str):
            The tag status, limited to one of the available
            string in TAG_STATUS
    """
    label = jsl.StringField(required=True)
    status = jsl.StringField(enum=TAG_STATUS, default='default')


class TagListSchema(jsl.Document):
    tags = jsl.ArrayField(jsl.DocumentField('TagSchema'))
