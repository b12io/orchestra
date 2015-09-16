from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission
from rest_framework_httpsignature.authentication import SignatureAuthentication

import logging
logger = logging.getLogger(__name__)


class SignedUser(AnonymousUser):
    pass


class IsSignedUser(BasePermission):

    def has_permission(self, request, view):
        return request.user and isinstance(request.user, SignedUser)


class OrchestraProjectAPIAuthentication(SignatureAuthentication):
    API_KEY_HEADER = 'X-Api-Key'

    def fetch_user_data(self, api_key):
        try:
            credentials = settings.ORCHESTRA_PROJECT_API_CREDENTIALS
            return (SignedUser(), credentials[api_key])
        except KeyError:
            raise AuthenticationFailed('Unable to find API key')
        except AttributeError:
            raise AuthenticationFailed(
                'Please configure settings.ORCHESTRA_PROJECT_API_CREDENTIALS')
