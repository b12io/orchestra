from rest_framework import filters


class QueryParamsFilterBackend(filters.BaseFilterBackend):
    """
    Takes queryparams from a URL, serializes into a python data structure
    and passes it as a queryset arguments
    """
    def filter_queryset(self, request, queryset, view):
        params = request.query_params.dict()
        serializer = view.get_serializer(data=params)
        serializer.is_valid()
        return queryset.filter(**serializer.data)
