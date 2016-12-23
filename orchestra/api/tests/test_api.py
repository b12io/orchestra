from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APIClient

from orchestra.models import Task
from orchestra.project_api.serializers import TaskSerializer
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import TaskFactory
from orchestra.tests.helpers.fixtures import UserFactory


class ModelViewSetTest(OrchestraTestCase):
    __test__ = False

    model = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_client = APIClient()
        self.user = UserFactory(username='test-api')
        self.api_client.force_authenticate(user=self.user)

        base_name = 'orchestra:api_new:{}'.format(self.model._meta.model_name)
        self.detail_endpoint = (
            lambda model_id: reverse('{}-detail'.format(base_name), model_id))
        self.list_endpoint = reverse('{}-list'.format(base_name))

    def test_endpoints(self):
        instance = self.factory()
        instance_data = self.serializer(instance).data

        response = self.api_client.get(self.list_endpoint(instance.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.api_client.get(self.detail_endpoint(instance.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        instance.delete()

        response = self.api_client.post(self.list_endpoint, instance_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.api_client.post(
            self.detail_endpoint(instance.id), instance_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TaskViewSetTest(ModelViewSetTest):
    __test__ = True

    model = Task
    serializer = TaskSerializer
    factory = TaskFactory
