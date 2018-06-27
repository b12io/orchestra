import jsl


class Predicate(jsl.Document):
    operator = jsl.StringField(required=True, pattern='!?=')
    value = jsl.AnyOfField([
        jsl.NumberField(),
        jsl.BooleanField(),
        jsl.StringField(),
        jsl.NullField()], required=True)


class TodoSchema(jsl.Document):
    id = jsl.IntField(required=True)
    description = jsl.StringField(required=True)
    items = jsl.ArrayField(jsl.DocumentField('TodoSchema'))
    skip_if = jsl.ArrayField(
        jsl.DictField(jsl.DocumentField(Predicate)))
    remove_if = jsl.ArrayField(
        jsl.DictField(jsl.DocumentField(Predicate)))


class TodoListSchema(jsl.Document):
    items = jsl.ArrayField(jsl.DocumentField('TodoSchema'))
