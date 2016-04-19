from django.conf import settings


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
