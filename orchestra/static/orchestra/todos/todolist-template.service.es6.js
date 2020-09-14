export default function todoListTemplateApi ($http) {
  const apiBase = '/orchestra/todos/'

  const list = () => {
    return `${apiBase}todolist_templates/`
  }

  const updateTodoListFromTemplate = () => {
    return `${apiBase}update_todos_from_todolist_template/`
  }

  return {
    updateTodoListFromTemplate: (data) => $http.post(updateTodoListFromTemplate(), data).then(response => response.data),
    list: (projectId) => $http.get(list())
      .then(response => response.data)
  }
};
