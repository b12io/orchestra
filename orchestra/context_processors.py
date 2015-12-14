from django.conf import settings


def google_analytics(request):
    """
    Provide the Google Analytics setting to any template that needs it.
    """
    return {
        'GOOGLE_ANALYTICS_KEY': settings.GOOGLE_ANALYTICS_KEY,
    }
