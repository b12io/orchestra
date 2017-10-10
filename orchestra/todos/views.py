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

    def get_queryset(self):
        queryset = Todo.objects.all()
        project_id = self.request.query_params.get('project', None)
        if project_id is not None:
            queryset = queryset.filter(task__project__id=int(project_id))
        queryset = queryset.order_by('-created_at')
        return queryset


class TodoDetail(generics.RetrieveUpdateDestroyAPIView):
    # TODO(marcua): Add orchestra.utils.view_helpers.IsAssociatedProject
    permission_classes = (permissions.IsAuthenticated,)
    queryset = Todo.objects.all()
    serializer_class = TodoSerializer
