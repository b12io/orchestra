export default function todoQaApi ($http) {
  const apiBase = '/orchestra/todos/todo_qa/'

  const listCreate = (projectId) => {
    if (projectId === undefined) {
      return apiBase
    }
    return `${apiBase}?project=${projectId}`
  }

  const details = (todoQaId) => `${apiBase}${todoQaId}/`
  const workerTaskRecentTodoQas = (taskId) => `/orchestra/todos/worker_task_recent_todo_qas/?task=${taskId}`

  return {
    create: (todoQa) => $http.post(listCreate(), todoQa)
      .then(response => response.data),
    update: (todoQa) => $http.put(details(todoQa.id), todoQa),
    workerTaskRecentTodoQas: (taskId) => $http.get(workerTaskRecentTodoQas(taskId))
      .then(response => response.data)
  }
};
