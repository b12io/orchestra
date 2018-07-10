export default function todoQaApi ($http) {
  const apiBase = '/orchestra/todos/todo_qa/'

  const listCreate = (projectId) => {
    if (projectId === undefined) {
      return apiBase
    }
    return `${apiBase}?project=${projectId}`
  }

  const details = (todoQaId) => `${apiBase}${todoQaId}/`
  const recommendations = (projectId) => `/orchestra/todos/recommendations/?project=${projectId}`

  return {
    create: (todoQa) => $http.post(listCreate(), todoQa)
      .then(response => response.data),
    list: (projectId) => $http.get(listCreate(projectId))
      .then(response => response.data),
    update: (todoQa) => $http.put(details(todoQa.id), todoQa),
    delete: (todoQa) => $http.delete(details(todoQa.id)),
    recommendations: (projectId) => $http.get(recommendations(projectId))
      .then(response => response.data)
  }
};
