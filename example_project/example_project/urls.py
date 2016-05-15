"""
example_project URL Configuration.

Registers all of the orchestra URLs so orchestra is usable when
`example_project` gets run. Additional URLs for other apps should be installed
here as well.
"""
from ajax_select import urls as ajax_select_urls
from django.conf import settings
from django.conf.urls import include
from django.conf.urls import url
from django.conf.urls import (
    handler400, handler403, handler404, handler500
)
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView

handler400 = 'orchestra.views.bad_request'  # noqa
handler403 = 'orchestra.views.forbidden'  # noqa
handler404 = 'orchestra.views.not_found'  # noqa
handler500 = 'orchestra.views.internal_server_error'  # noqa

urlpatterns = [

    # Admin Views
    url(r'^orchestra/admin/',
        include(admin.site.urls)),
    url(r'^ajax_select/', include(ajax_select_urls)),


    # Registration Views
    # Eventually these will be auto-registered with the Orchestra URLs, but for
    # now we need to add them separately.
    url(r'^orchestra/accounts/',
        include('registration.backends.default.urls')),

    # Optionally include these routes to enable user hijack functionality.
    url(r'^orchestra/switch/', include('hijack.urls')),

    # Logout then login is not available as a standard django
    # registration route.
    url(r'^orchestra/accounts/logout_then_login/$',
        auth_views.logout_then_login,
        name='logout_then_login'),

    # Orchestra URLs
    url(r'^orchestra/',
        include('orchestra.urls', namespace='orchestra')),

    # Beanstalk Dispatch URLs
    url(r'^beanstalk_dispatch/',
        include('beanstalk_dispatch.urls')),

    # Favicon redirect for crawlers
    url(r'^favicon.ico/$', RedirectView.as_view(
        url=settings.STATIC_URL + 'orchestra/icons/favicon.ico',
        permanent=True),
        name='favicon'),
]
