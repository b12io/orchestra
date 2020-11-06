from rest_framework import filters


class QueryParamsFilterBackend(filters.BaseFilterBackend):
    """
    Takes queryparams from a URL, serializes into a python data structure
    and passes it as a queryset arguments
    """
    def _get_filter_kwargs(self, view, params):
        serializer = view.get_serializer(data=params)
        serializer.is_valid()
        return serializer.data

    def filter_queryset(self, request, queryset, view):
        params = request.query_params.dict()
        qs_kwargs = self._get_filter_kwargs(view, params)
        return queryset.filter(**qs_kwargs)
