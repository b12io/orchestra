import jsl


class PredicateSchema(jsl.Document):
    """
    A predicate schema

    Attributes:
        operator (str):
            Specify the compare operator of predicate.
            Supported predicates are >, <, >=, <=, !=, and ==.
        value (number, bool, sring, or None):
            The value to compare with of the predicate.
    """
    operator = jsl.StringField(required=True, pattern='[!=><]=|[><]')
    value = jsl.AnyOfField([
        jsl.NumberField(),
        jsl.BooleanField(),
        jsl.StringField(),
        jsl.NullField()], required=True)


class TodoSchema(jsl.Document):
    """
    A Todo schema

    Attributes:
        id (int):
            A unique id for the todo.
        description (str):
            A text description of the todo.
        items (array):
            An array of sub-todos of this todo.
        skip_if (array):
            An array of conditions to skip this todo. If any of the
            condition is true, the todo is skipped. Each condition is a
            dictionary of attributes and predicates which get ANDed together.
        remove_if (array):
            An array of conditions to remove this todo. If any of the
            condition is true, the todo is removed. Each condition is a
            dictionary of attributes and predicates which get ANDed together.
    """
    id = jsl.IntField(required=True)
    description = jsl.StringField(required=True)
    items = jsl.ArrayField(jsl.DocumentField('TodoSchema'))
    skip_if = jsl.ArrayField(
        jsl.DictField(
            pattern_properties={'.*': jsl.DocumentField('PredicateSchema')}))
    remove_if = jsl.ArrayField(
        jsl.DictField(
            pattern_properties={'.*': jsl.DocumentField('PredicateSchema')}))


class TodoListSchema(jsl.Document):
    items = jsl.ArrayField(jsl.DocumentField('TodoSchema'))


class TodoActionSchema(jsl.Document):
    """
    A todo action schema

    Attributes:
        action (str):
            Specify the action taken by the worker on the given todo.
            Examples: skip, unskip, complete, incomplete
        datetime (datetime):
            The time the action was taken.
        step_slug (str):
            Unique identifier for the workflow step that the task represents.
    """
    action = jsl.StringField(required=True)
    datetime = jsl.DateTimeField(required=True)
    step_slug = jsl.StringField(required=True)


class TodoActionListSchema(jsl.Document):
    actions = jsl.ArrayField(jsl.DocumentField('TodoActionSchema'))
