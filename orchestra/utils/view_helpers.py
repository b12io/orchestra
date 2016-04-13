from rest_framework import filters
from rest_framework import permissions

from orchestra.models import Worker


class IsAssociatedWorker(permissions.BasePermission):
    """
    Permission for objects with `worker` field. Checks if request.user matches
    worker on object.
    """

    def has_object_permission(self, request, view, obj):
        worker = Worker.objects.get(user=request.user)
        return obj.worker == worker


class NotDeletedFilterBackend(filters.BaseFilterBackend):
    """
    Filter that only allows non-deleted items.
    """
    def filter_queryset(self, request, queryset, view):
        return queryset.filter(is_deleted=False)


class MarkDeletedDestroyMixin(object):
    """
    Overrides DestroyModelMixin to set is_deleted=True instead of
    deleting the model instance.
    """

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save()
