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
