"""
example_project URL Configuration.

Registers all of the orchestra URLs so orchestra is usable when
`example_project` gets run. Additional URLs for other apps should be installed
here as well.
"""
from django.conf.urls import include, url
from django.contrib.auth import views as auth_views

urlpatterns = [

    # Registration Views
    # Eventually these will be auto-registered with the Orchestra URLs, but for
    # now we need to add them separately.
    url(r'^orchestra/accounts/',
        include(
            'registration.backends.default.urls')),

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
]
