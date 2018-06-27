from datetime import datetime
import logging
from pydoc import locate

from orchestra.models import TodoListTemplate
from orchestra.models import Todo
from orchestra.models import Task

logger = logging.getLogger(__name__)


def add_todolist_template(todolist_template_slug, task_id):
    todolist_template = TodoListTemplate.objects.get(
        slug=todolist_template_slug)
    cond_props = {}
    path = todolist_template.conditional_property_function.get(
        'path', None)
    if path:
        try:
            get_cond_props = locate(path)
            kwargs = todolist_template.conditional_property_function.get(
                'kwargs', {})
            cond_props = get_cond_props(**kwargs)
        except Exception:
            logger.exception('Invalid condition function path.')

    task = Task.objects.get(id=task_id)
    template_todos = todolist_template.todos.get('items', [])
    root_todo = Todo(
        task=task,
        description=todolist_template.name,
        template=todolist_template
    )
    root_todo.save()
    for template_todo in template_todos:
        _add_template_todo(
            template_todo, todolist_template, root_todo, task, cond_props)


def _to_exclude(props, conditions=[]):
    for condition in conditions:
        for prop, predicate in condition:
            current_value = props.get(prop)
            compared_to_value = predicate['value']
            if predicate['operator'] == '=':
                return current_value == compared_to_value
            elif predicate['operator'] == '!=':
                return current_value != compared_to_value
    return False


def _add_template_todo(
        template_todo, todolist_template,
        parent_todo, task, conditional_props):
    remove = _to_exclude(conditional_props, template_todo.get('remove_if', []))
    if not remove:
        skipped_datetime = datetime.now() if _to_exclude(
                conditional_props, template_todo.get('skip_if', [])) else None
        todo = Todo(
            task=task,
            description=template_todo['description'],
            template=todolist_template,
            parent_todo=parent_todo,
            skipped_datetime=skipped_datetime
        )
        todo.save()
        for template_todo_item in template_todo.get('items', []):
            _add_template_todo(
                template_todo_item, todolist_template, todo,
                task, conditional_props)
