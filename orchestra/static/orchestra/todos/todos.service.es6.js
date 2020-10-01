export default function todoApi ($http) {
  const apiBase = '/orchestra/todos/todo/'

  const listCreate = (projectId) => {
    if (projectId === undefined) {
      return apiBase
    }
    return `${apiBase}?project=${projectId}`
  }

  const details = (todoId) => `${apiBase}${todoId}/`

  return {
    create: (todo) => $http.post(listCreate(), todo)
      .then(response => response.data),
    list: (projectId) => $http.get(listCreate(projectId), {cache: true})
      .then(response => response.data),
    update: (todo) => $http.put(details(todo.id), todo),
    delete: (todo) => $http.delete(details(todo.id))
  }
};
