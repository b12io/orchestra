import django_filters

from rest_framework import filters

from orchestra.models import TimeEntry


class TimeEntryFilter(filters.FilterSet):
    min_date = django_filters.DateFilter(name='date', lookup_expr='gte')
    max_date = django_filters.DateFilter(name='date', lookup_expr='lte')

    class Meta:
        model = TimeEntry
        fields = ['min_date', 'max_date']
