from rest_framework import filters


class TodoFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        params = request.query_params.dict()
        serializer = view.get_serializer(data=params, **view.kwargs)
        serializer.is_valid()
        return queryset.filter(**serializer.data)
