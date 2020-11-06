from rest_framework.test import APIRequestFactory
from rest_framework.viewsets import ModelViewSet

from orchestra.models import TodoQA
from orchestra.tests.helpers.fixtures import TodoFactory
from orchestra.tests.helpers.fixtures import ProjectFactory
from orchestra.tests.helpers.fixtures import TodoQAFactory
from orchestra.orchestra_api import build_url_params
from orchestra.todos.filters import QueryParamsFilterBackend
from orchestra.todos.serializers import TodoQASerializer
from orchestra.tests.helpers import OrchestraTransactionTestCase


factory = APIRequestFactory()


class DummyView(ModelViewSet):
    model = TodoQA
    serializer_class = TodoQASerializer
    queryset = TodoQA.objects.all()


class QueryParamsFilterBackendTests(OrchestraTransactionTestCase):
    def _get_qs_kwargs(self, url_params):
        url = '/some-path/{}'.format(url_params)
        view = DummyView(action_map={'get': 'list'})
        request = factory.get(url)
        request = view.initialize_request(request)
        view.request = request
        view.format_kwarg = {}
        backend = QueryParamsFilterBackend()
        qs_kwargs = backend._get_filter_kwargs(
            view, request.query_params.dict())
        return qs_kwargs

    def test_random_key_values(self):
        TodoQAFactory()
        TodoQAFactory()
        url_params = build_url_params(
            123, 'slug', **{'some_random_key': 'some_value'})
        qs_kwargs = self._get_qs_kwargs(url_params)
        self.assertEqual(qs_kwargs, {})

    def test_only_serializer_fields_are_passed(self):
        comment = 'Some comment'
        project = ProjectFactory()
        todo = TodoFactory(project=project)
        TodoQAFactory(todo=todo, comment=comment)
        url_params = build_url_params(
            todo.project.id,
            None,
            **{
                'todo': todo.id,
                'comment': comment,
                'non_existing_field': True})
        qs_kwargs = self._get_qs_kwargs(url_params)
        self.assertEqual(qs_kwargs, {'todo': str(todo.id), 'comment': comment})
