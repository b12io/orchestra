from rest_framework import filters


class TodoFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        params = request.query_params.dict()
        key_values = {}
        for field, value in params.items():
            if value == 'None':
                value = None
            elif isinstance(value, str) and value.isdigit():
                try:
                    key_values[field] = int(value)
                except ValueError:
                    key_values[field] = float(value)
            else:
                key_values[field] = value
        return queryset.filter(**key_values)
