from django.db import transaction
import logging
import operator
from pydoc import locate

from orchestra.models import TodoListTemplate
from orchestra.models import Todo
from orchestra.models import Project
from orchestra.utils.common_helpers import get_step_by_project_id_and_step_slug

logger = logging.getLogger(__name__)

OPERATORS = {
    '<': operator.lt,
    '<=': operator.le,
    '==': operator.eq,
    '!=': operator.ne,
    '>=': operator.ge,
    '>': operator.gt
}


@transaction.atomic
def add_todolist_template(todolist_template_slug, project_id,
                          step_slug, additional_data=None):
    todolist_template = TodoListTemplate.objects.get(
        slug=todolist_template_slug)

    project = Project.objects.get(id=project_id)
    step = get_step_by_project_id_and_step_slug(project_id, step_slug)
    template_todos = todolist_template.todos.get('items', [])
    additional_data = additional_data if additional_data else {}
    root_todo = Todo(
        project=project,
        step=step,
        title=todolist_template.name,
        template=todolist_template,
        additional_data=additional_data,
        status=Todo.Status.PENDING.value
    )
    root_todo.save()

    cond_props = {}
    path = todolist_template.conditional_property_function.get(
        'path', None)
    if path:
        try:
            get_cond_props = locate(path)
            cond_props = get_cond_props(project)
        except Exception:
            logger.exception('Invalid conditional function path.')
    for template_todo in template_todos:
        _add_template_todo(
            template_todo, todolist_template,
            root_todo, project, step, cond_props, additional_data)


def _to_exclude(props, conditions):
    """
    The conditions is it a list of conditions that get ORed together,
    with predicates in each dictionary getting ANDed.
    """
    any_condition_true = False

    for condition in conditions:
        all_props_true = len(condition) > 0
        for prop, predicate in condition.items():
            current_value = props.get(prop)
            compared_to_value = predicate['value']
            compare = OPERATORS[predicate['operator']]
            all_props_true = (
                all_props_true and
                compare(current_value, compared_to_value))
        any_condition_true = any_condition_true or all_props_true

    return any_condition_true


def _add_template_todo(
        template_todo, todolist_template,
        parent_todo, project, step, conditional_props,
        additional_data):
    remove = _to_exclude(conditional_props, template_todo.get('remove_if', []))
    if not remove:
        if parent_todo.status == Todo.Status.DECLINED.value:
            to_skip = True
        else:
            to_skip = _to_exclude(
                conditional_props, template_todo.get('skip_if', []))

        if to_skip:
            status = Todo.Status.DECLINED.value
        else:
            status = Todo.Status.PENDING.value
        todo = Todo(
            project=project,
            step=step,
            title=template_todo['description'],
            slug=template_todo.get('slug'),
            template=todolist_template,
            parent_todo=parent_todo,
            status=status,
            additional_data=additional_data
        )
        todo.save()
        for template_todo_item in template_todo.get('items', []):
            _add_template_todo(
                template_todo_item, todolist_template, todo,
                project, step, conditional_props, additional_data)
