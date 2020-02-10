import django_filters

from orchestra.models import TimeEntry


class TimeEntryFilter(django_filters.FilterSet):
    min_date = django_filters.DateFilter(field_name='date', lookup_expr='gte')
    max_date = django_filters.DateFilter(field_name='date', lookup_expr='lte')

    class Meta:
        model = TimeEntry
        fields = ['min_date', 'max_date']
