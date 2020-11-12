from rest_framework.test import APIRequestFactory
from rest_framework.viewsets import ModelViewSet

from orchestra.models import Todo
from orchestra.models import TodoQA
from orchestra.tests.helpers.fixtures import TodoFactory
from orchestra.tests.helpers.fixtures import ProjectFactory
from orchestra.orchestra_api import build_url_params
from orchestra.todos.filters import QueryParamsFilterBackend
from orchestra.todos.serializers import TodoQASerializer
from orchestra.tests.helpers import OrchestraTransactionTestCase
from orchestra.todos.views import GenericTodoViewset


factory = APIRequestFactory()


class DummyView(ModelViewSet):
    model = TodoQA
    serializer_class = TodoQASerializer
    queryset = TodoQA.objects.all()


class QueryParamsFilterBackendTests(OrchestraTransactionTestCase):
    def _get_qs_kwargs(self, view_class, url_params):
        url = '/some-path/{}'.format(url_params)
        view = view_class(action_map={'get': 'list'})
        request = factory.get(url)
        request = view.initialize_request(request)
        view.request = request
        view.format_kwarg = {}
        backend = QueryParamsFilterBackend()
        params = backend._get_params(request, view)
        kwargs = backend._get_kwargs(view, params)
        return kwargs

    def test_random_key_values(self):
        url_params = build_url_params(
            123, 'slug', **{'some_random_key': 'some_value'})
        kwargs = self._get_qs_kwargs(DummyView, url_params)
        self.assertEqual(kwargs, {})

    def test_only_serializer_fields_are_passed(self):
        """
        In GenericTodoViewset we have the following filterset_fields:
        filterset_fields = ('project__id', 'step__slug',)
        A field which is not specified in it or in the view's
        serializer fields cannot be passed as a filter args
        """
        title = 'Some title'
        project_id = 123
        url_params = build_url_params(
            project_id,
            None,
            **{
                'title': title,
                'nonexistent_field': True})
        kwargs = self._get_qs_kwargs(
            GenericTodoViewset, url_params)
        self.assertEqual(
            kwargs, {'project__id': str(project_id), 'title': title})

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
        kwargs = self._get_qs_kwargs(
            GenericTodoViewset, url_params)
        # kwargs doesn't contain additional_data__sql field
        self.assertEqual(kwargs, {'project__id': str(project.id)})

        url_params = build_url_params(
            project.id,
            None,
            **{'title': dangerous_sql})
        kwargs = self._get_qs_kwargs(
            GenericTodoViewset, url_params)
        todos = Todo.objects.filter(**kwargs)
        self.assertEqual(
            kwargs,
            {'project__id': str(project.id), 'title': dangerous_sql})
        self.assertTrue(todos.count, 0)
