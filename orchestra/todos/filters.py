from ast import literal_eval

from rest_framework import filters


class QueryParamsFilterBackend(filters.BaseFilterBackend):
    """
    Takes queryparams from a URL, serializes into a python data structure
    and passes it as a queryset arguments.
    Note: this doesn't support nested__fields. To support them,
    add `filterset_fields` iterable to the view.
    Note: nested__field lookup in JSONField is not supported even if added
    to the `filterset_fields`.
    This issue can be fixed when we migrate to Django 3.1
    and convert additional_data from django-jsonfields to the native one.
    """
    def _get_filter_kwargs(self, view, params):
        serializer = view.get_serializer(data=params)
        serializer.is_valid()
        return serializer.data

    def _get_filterset_fields_kwargs(self, view, params, qs_kwargs):
        filterset_kwargs = {}
        if hasattr(view, 'filterset_fields'):
            for field in view.filterset_fields:
                if field in params and field not in qs_kwargs:
                    filterset_kwargs[field] = params[field]
        return filterset_kwargs

    def _get_params(self, request):
        params = {}
        for key, value in request.query_params.items():
            params[key] = literal_eval(value)
        return params

    def filter_queryset(self, request, queryset, view):
        params = self._get_params(request)
        qs_kwargs = self._get_filter_kwargs(view, params)
        filterset_kwargs = self._get_filterset_fields_kwargs(
            view, params, qs_kwargs)
        qs_kwargs.update(filterset_kwargs)
        return queryset.filter(**qs_kwargs)
