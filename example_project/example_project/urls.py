"""
example_project URL Configuration.

Registers all of the orchestra URLs so orchestra is usable when
`example_project` gets run. Additional URLs for other apps should be installed
here as well.
"""
from ajax_select import urls as ajax_select_urls
from django.conf import settings
from django.conf.urls import handler400
from django.conf.urls import handler403
from django.conf.urls import handler404
from django.conf.urls import handler500
from django.conf.urls import include
from django.urls import re_path
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView

handler400 = 'orchestra.views.bad_request'  # noqa
handler403 = 'orchestra.views.forbidden'  # noqa
handler404 = 'orchestra.views.not_found'  # noqa
handler500 = 'orchestra.views.internal_server_error'  # noqa

urlpatterns = [

    # Admin Views
    re_path(r'^orchestra/admin/', admin.site.urls),
    re_path(r'^ajax_select/', include(ajax_select_urls)),


    # Registration Views
    # Eventually these will be auto-registered with the Orchestra URLs, but for
    # now we need to add them separately.
    re_path(r'^orchestra/accounts/',
        include('registration.backends.default.urls')),

    # Optionally include these routes to enable user hijack functionality.
    re_path(r'^orchestra/switch/', include('hijack.urls')),

    # Logout then login is not available as a standard django
    # registration route.
    re_path(r'^orchestra/accounts/logout_then_login/$',
        auth_views.logout_then_login,
        name='logout_then_login'),

    # Orchestra URLs
    re_path(r'^orchestra/',
        include('orchestra.urls', namespace='orchestra')),

    # Beanstalk Dispatch URLs
    re_path(r'^beanstalk_dispatch/',
        include('beanstalk_dispatch.urls')),

    # Favicon redirect for crawlers
    re_path(r'^favicon.ico/$', RedirectView.as_view(
        url=settings.STATIC_URL + 'orchestra/icons/favicon.ico',
        permanent=True),
        name='favicon'),
]
