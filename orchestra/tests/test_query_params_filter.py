from rest_framework.test import APIRequestFactory
from rest_framework.viewsets import ModelViewSet

from orchestra.models import Worker
from orchestra.models import TodoQA
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
    def test_random_key_values(self):
        TodoQAFactory()
        TodoQAFactory()
        url_params = build_url_params(
            123, 'slug', **{'some_random_key': 'some_value'})
        url = '/some-path/{}'.format(url_params)
        view = DummyView(action_map={'get': 'list'})
        request = factory.get(url)
        request = view.initialize_request(request)
        view.request = request
        view.format_kwarg = {}
        backend = QueryParamsFilterBackend()
        qs_kwargs = backend._get_filter_kwargs(
            view, request.query_params.dict())
        self.assertEqual(qs_kwargs, {})
