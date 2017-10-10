from rest_framework import generics
from rest_framework import permissions

from orchestra.models import Todo
from orchestra.todos.serializers import TodoSerializer


class TodoList(generics.ListCreateAPIView):
    # TODO(marcua): Add orchestra.utils.view_helpers.IsAssociatedProject
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = TodoSerializer
    queryset = Todo.objects.all()
    # filter_backends = (filters.DjangoFilterBackend,)
    # filter_class = TimeEntryFilter


class TodoDetail(generics.RetrieveUpdateDestroyAPIView):
    # TODO(marcua): Add orchestra.utils.view_helpers.IsAssociatedProject
    permission_classes = (permissions.IsAuthenticated,)
    queryset = Todo.objects.all()
    serializer_class = TodoSerializer
