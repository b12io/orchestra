import csv
import json

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from tempfile import NamedTemporaryFile

from orchestra.core.errors import TodoListTemplateValidationError
from orchestra.google_apps.permissions import write_with_link_permission
from orchestra.google_apps.service import Service
from orchestra.google_apps.convenience import get_google_spreadsheet_as_csv
from orchestra.models import TodoListTemplateImportRecord


REMOVE_IF_HEADER = 'Remove if'
SKIP_IF_HEADER = 'Skip if'


def _write_template_rows(writer, todo, depth):
    """Recursively emits the rows of a to-do list template to the
    CSV `writer`. The format of each row is described in
    `export_to_spreadsheet` below. The `depth` of this row
    dictates the number of empty cells by which to indent
    this row's description.
    """
    writer.writerow(
        [json.dumps(todo.get('remove_if', [])),
         json.dumps(todo.get('skip_if', []))] +
        ([''] * depth) +
        [todo.get('description', '')])
    # `reversed` iteration because the JSON-serialized order of
    # children is the opposite of the top-to-bottom order in the
    # spreadsheet.
    for child in reversed(todo.get('items', [])):
        _write_template_rows(writer, child, depth + 1)


def _upload_csv_to_google(spreadsheet_name, file):
    service = Service(settings.GOOGLE_P12_PATH,
                      settings.GOOGLE_SERVICE_EMAIL)
    sheet = service.insert_file(
        spreadsheet_name,
        '',
        settings.ORCHESTRA_TODO_LIST_TEMPLATE_EXPORT_GDRIVE_FOLDER,
        'text/csv',
        'application/vnd.google-apps.spreadsheet',
        file.name
    )
    service.add_permission(sheet['id'], write_with_link_permission)
    return sheet['alternateLink']


def export_to_spreadsheet(todo_list_template):
    """
    Recursively descend down the to-do tree of a `todo_list_template`
    and add a row per to-do to a CSV, uploading it to a Google Sheet
    when done. The first two columns of the sheet capture json-encoded
    remove_if and skip_if logic. After that, the text in the `i`'th
    column represents a to-do's title that is `i` levels nested in the
    to-do tree.
    """
    with NamedTemporaryFile(mode='w+', delete=False) as file:
        writer = csv.writer(file)
        writer.writerow([REMOVE_IF_HEADER, SKIP_IF_HEADER])
        _write_template_rows(writer, todo_list_template.todos, 0)
        file.flush()
        return _upload_csv_to_google(
            '{} - {}'.format(todo_list_template.name, timezone.now()),
            file)


def import_from_spreadsheet(todo_list_template, spreadsheet_url, request):
    """Imports a Google Sheet at `spreadsheet_url` to
    `todo_list_template.todos`.

    For debugging/provenance purposes, creates a
    TodoListTemplateImportRecord with the user, todo_list_template,
    and spreadsheet URL behind the import.
    """
    try:
        reader = get_google_spreadsheet_as_csv(
            spreadsheet_url, reader=csv.reader)
    except ValueError as e:
        raise TodoListTemplateValidationError(e)
    header = next(reader)
    if header[:2] != [REMOVE_IF_HEADER, SKIP_IF_HEADER]:
        raise TodoListTemplateValidationError(
            'Unexpected header: {}'.format(header))
    # The `i`'th entry in parent_items is current list of child to-dos
    # of the `i`-depth parent. We use this to determine which parent
    # to add a child to when we read to-do in a row with lower
    # indentation than its parent.
    parent_items = []
    todos = None
    for rowindex, row in enumerate(reader):
        item = {
            'id': rowindex,
            'remove_if': json.loads(row[0] or '[]'),
            'skip_if': json.loads(row[1] or '[]'),
            'items': []
        }
        nonempty_columns = [(columnindex, text)
                            for columnindex, text in enumerate(row[2:])
                            if text]
        if len(nonempty_columns) == 0:
            continue
        elif len(nonempty_columns) > 1:
            raise TodoListTemplateValidationError(
                'More than one text entry in row {}: {}'.format(
                    rowindex, row))

        # `nonempty_index` is the depth of the column that contains
        # text in this row. We use that depth to determine which to-do
        # this is a child of.
        nonempty_index = nonempty_columns[0][0]
        item['description'] = nonempty_columns[0][1]

        if todos is None:
            # If todos has not yet been defined, `item` is the root.
            todos = item
        elif nonempty_index <= len(parent_items):
            # If the depth of the row is at most one larger than its
            # parent's depth, we can look at `parent_items` to
            # determine its parent. We truncate any parent_items entry
            # that's deeper than this item, as it is no longer
            # possible for deeper items to be parents of subsequent rows.
            parent_items = parent_items[:nonempty_index]
            # Insert this item into its parent's list of children.
            # Because child ordering is reversed in our
            # serialization format, insert it at the beginning of the
            # list of children.
            parent_items[-1].insert(0, item)
        else:
            # You can't be deeper than one column past the previous
            # row's depth.
            raise TodoListTemplateValidationError(
                'Row {} has skipped some columns in depth: {}'.format(
                    rowindex, row))
        # Add this item's child list to the end of the list of
        # parents, in case it ends up with children in subsequent rows.
        parent_items.append(item['items'])

    todo_list_template.todos = todos
    with transaction.atomic():
        todo_list_template.save()
        TodoListTemplateImportRecord.objects.create(
            import_url=spreadsheet_url,
            todo_list_template=todo_list_template,
            importer=request.user)
