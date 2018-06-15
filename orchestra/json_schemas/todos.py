import jsl


class TodoSchema(jsl.Document):
    id = jsl.IntField()
    description = jsl.StringField()
    items = jsl.ArrayField(jsl.DocumentField('TodoSchema'))


class TodoListSchema(jsl.Document):
    items = jsl.ArrayField(jsl.DocumentField('TodoSchema'))
