from django.conf.urls import include
from django.conf.urls import patterns
from django.conf.urls import url
from orchestra.views import index
from orchestra.views import status
from orchestra.admin_views import project_details


urlpatterns = patterns(
    '',
    url(r'^api/',
        include('orchestra.api_urls', namespace='orchestra')),
    url(r'^app/?', index, name='index'),
    # TODO(marcua): Unify `project_details` into `api_urls` under `admin_api`
    # or something like that, since it's just another api.
    url(r'^project_details/(?P<project_id>\d+)',
        project_details,
        name='project_details'),
    url(r'^status/', status, name='status')
)
