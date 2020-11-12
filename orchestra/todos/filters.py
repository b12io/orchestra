import json

from rest_framework import filters


class QueryParamsFilterBackend(filters.BaseFilterBackend):
    """
    Takes a json-encoded data as a queryparam from a URL,
    serializes into a python data structure
    and passes it as a queryset arguments.
    Format: ?q='{"key": ["val1", "val2"], "key2": null}', where `q` is
    filter_prefix which can be set in the view:
    filter_prefix = 'custom_key'
    Note: this doesn't support nested__fields. To support them,
    add `filterset_fields` iterable to the view.
    Note: nested__field lookup in JSONField is not supported even if added
    to the `filterset_fields`.
    This issue can be fixed when we migrate to Django 3.1
    and convert additional_data from django-jsonfields to the native one.
    """
    def _get_query_params_prefix(self, view):
        """
        By default, filter params are assigned to `q` parameter.
        """
        if hasattr(view, 'filter_prefix'):
            return view.filter_prefix
        return 'q'

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

    def _get_params(self, request, view):
        """
        Here we get JSON encoded params and encode them into Python objects.
        """
        params = request.query_params.copy().dict()
        json_params = params.pop(self._get_query_params_prefix(view), '{}')
        converted = json.loads(json_params)
        params.update(converted)
        return params

    def _get_kwargs(self, view, params):
        qs_kwargs = self._get_filter_kwargs(view, params)
        filterset_kwargs = self._get_filterset_fields_kwargs(
            view, params, qs_kwargs)
        qs_kwargs.update(filterset_kwargs)
        return qs_kwargs

    def filter_queryset(self, request, queryset, view):
        params = self._get_params(request, view)
        kwargs = self._get_kwargs(view, params)
        return queryset.filter(**kwargs)
