from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from rest_framework import status

from orchestra.models import Worker
from orchestra.tests.helpers import OrchestraTestCase

UserModel = get_user_model()


class OrchestraRegistrationViewTests(OrchestraTestCase):

    def setUp(self):
        super().setUp()
        self.url = reverse('orchestra:registration_register')

    def get_valid_post_data(self):
        return {
            'username': 'test',
            'email': 'test@test.com',
            'password1': 'test',
            'password2': 'test',  # password confirmation
        }

    def assert_valid_form(self, resp):
        # This asserts that the form is valid since we redirect
        self.assertRedirects(resp, reverse('registration_complete'))

    def assert_related_obj_count(self, count):
        self.assertEqual(UserModel.objects.all().count(), count)
        self.assertEqual(Worker.objects.all().count(), count)

    def assert_models(self, post_data, count=1):
        """
            On a successful register we expect the following:
            1. A User object is created with the form_data we give
            2. A Worker object is associated with this User
        """
        user = UserModel.objects.get(username=post_data.get('username'))
        self.assertEqual(user.email, post_data.get('email'))
        self.assertTrue(user.check_password(post_data.get('password1')))
        self.assertTrue(Worker.objects.filter(user=user).exists())

        self.assert_related_obj_count(count)

    def test_worker_created(self):
        post_data = self.get_valid_post_data()
        resp = self.request_client.post(self.url, post_data)

        self.assert_valid_form(resp)
        self.assert_models(post_data)

    def test_multiple_workers_created(self):
        post_data = self.get_valid_post_data()
        resp = self.request_client.post(self.url, post_data)

        self.assert_valid_form(resp)
        self.assert_models(post_data)

        post_data = self.get_valid_post_data()
        post_data['username'] = 'new_{}'.format(post_data.get('username'))
        post_data['email'] = 'new_{}'.format(post_data.get('email'))
        post_data['password1'] = 'new_{}'.format(post_data.get('password1'))
        post_data['password2'] = 'new_{}'.format(post_data.get('password2'))

        resp = self.request_client.post(self.url, post_data)

        self.assert_valid_form(resp)
        self.assert_models(post_data, count=2)

    def test_invalid_no_worker(self):
        post_data = self.get_valid_post_data()
        post_data['username'] = ''
        self.request_client.post(self.url, post_data)
        self.assert_related_obj_count(0)

    def test_duplicate_register(self):
        post_data = self.get_valid_post_data()

        resp = self.request_client.post(self.url, post_data)

        self.assert_valid_form(resp)
        self.assert_models(post_data)

        resp = self.request_client.post(self.url, post_data)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assert_related_obj_count(1)
