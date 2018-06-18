import jsl


class TodoSchema(jsl.Document):
    id = jsl.IntField(required=True)
    description = jsl.StringField(required=True)
    items = jsl.ArrayField(jsl.DocumentField('TodoSchema'))


class TodoListSchema(jsl.Document):
    items = jsl.ArrayField(jsl.DocumentField('TodoSchema'))
