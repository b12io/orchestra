export default function todoListTemplateApi ($http) {
  const apiBase = '/orchestra/todos/'

  const list = () => {
    return `${apiBase}todolist_templates/`
  }

  const addTodoListTemplate = () => {
    return `${apiBase}add_todos_from_todolist_template/`
  }

  return {
    addTodoListTemplate: (data) => $http.post(addTodoListTemplate(), data)
      .then(response => response.data),
    list: (projectId) => $http.get(list())
      .then(response => response.data)
  }
};
