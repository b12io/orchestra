from django.conf import settings

from orchestra.interface_api.project_management.decorators import \
    is_project_admin


def google_analytics(request):
    """
    Provide the Google Analytics setting to any template that needs it.
    """
    return {
        'GOOGLE_ANALYTICS_KEY': settings.GOOGLE_ANALYTICS_KEY,
    }


def third_party_scripts(request):
    """
    Provide the path to common third party scripts to any template that needs
    it.
    """
    return {
        'ORCHESTRA_THIRD_PARTY_SCRIPTS_TEMPLATE':
        settings.ORCHESTRA_THIRD_PARTY_SCRIPTS_TEMPLATE
    }


def base_context(request):
    """
    Provide context variables for use across all views.
    """
    if not hasattr(request, 'user'):
        return {}
    return {
        'is_project_admin': is_project_admin(request.user)
    }
