from rest_framework.test import APIRequestFactory
from rest_framework.viewsets import ModelViewSet

from orchestra.models import Todo
from orchestra.models import TodoQA
from orchestra.tests.helpers.fixtures import TodoFactory
from orchestra.tests.helpers.fixtures import ProjectFactory
from orchestra.orchestra_api import build_url_params
from orchestra.todos.filters import QueryParamsFilterBackend
from orchestra.todos.serializers import TodoQASerializer
from orchestra.todos.serializers import BulkTodoSerializer
from orchestra.tests.helpers import OrchestraTransactionTestCase


factory = APIRequestFactory()


class DummyView(ModelViewSet):
    model = TodoQA
    serializer_class = TodoQASerializer
    queryset = TodoQA.objects.all()


class DummyView2(ModelViewSet):
    model = Todo
    serializer_class = BulkTodoSerializer
    queryset = Todo.objects.all()


class QueryParamsFilterBackendTests(OrchestraTransactionTestCase):
    def _get_qs_kwargs(self, view_class, url_params):
        url = '/some-path/{}'.format(url_params)
        view = view_class(action_map={'get': 'list'})
        request = factory.get(url)
        request = view.initialize_request(request)
        view.request = request
        view.format_kwarg = {}
        backend = QueryParamsFilterBackend()
        qs_kwargs = backend._get_filter_kwargs(
            view, request.query_params.dict())
        return qs_kwargs

    def test_random_key_values(self):
        url_params = build_url_params(
            123, 'slug', **{'some_random_key': 'some_value'})
        qs_kwargs = self._get_qs_kwargs(DummyView, url_params)
        self.assertEqual(qs_kwargs, {})

    def test_only_serializer_fields_are_passed(self):
        comment = 'Some comment'
        todo_id = 123
        url_params = build_url_params(
            111,
            None,
            **{
                'todo': todo_id,
                'comment': comment,
                'nonexistent_field': True})
        qs_kwargs = self._get_qs_kwargs(DummyView, url_params)
        self.assertEqual(qs_kwargs, {'todo': str(todo_id), 'comment': comment})

    def test_dangerous_sql(self):
        project = ProjectFactory()
        TodoFactory(project=project)
        dangerous_sql = (
            "if ((select user) = 'sa'"
            " OR (select user) = 'dbo') select 1 else select 1/0"
        )
        url_params = build_url_params(
            project.id,
            None,
            **{'additional_data__sql': dangerous_sql}
        )
        qs_kwargs = self._get_qs_kwargs(DummyView2, url_params)
        # qs_kwargs doesn't contain additional_data__sql field
        self.assertEqual(qs_kwargs, {'project': str(project.id)})

        url_params = build_url_params(
            project.id,
            None,
            **{'title': dangerous_sql})
        qs_kwargs = self._get_qs_kwargs(DummyView2, url_params)
        todos = Todo.objects.filter(**qs_kwargs)
        self.assertEqual(
            qs_kwargs, {'project': str(project.id), 'title': dangerous_sql})
        self.assertTrue(todos.count, 0)
