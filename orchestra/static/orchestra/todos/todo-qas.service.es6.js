export default function todoQAApi ($http) {
  const apiBase = '/orchestra/todos/todo_qa/'

  const listCreate = (projectId) => {
    if (projectId === undefined) {
      return apiBase
    }
    return `${apiBase}?project=${projectId}`
  }

  const details = (todoQAId) => `${apiBase}${todoQAId}/`
  const recommendations = (projectId) => `/orchestra/todos/recommendations/?project=${projectId}`

  return {
    create: (todoQA) => $http.post(listCreate(), todoQA)
      .then(response => response.data),
    list: (projectId) => $http.get(listCreate(projectId))
      .then(response => response.data),
    update: (todoQA) => $http.put(details(todoQA.id), todoQA),
    delete: (todoQA) => $http.delete(details(todoQA.id)),
    recommendations: (projectId) => $http.get(recommendations(projectId))
      .then(response => response.data)
  }
};
