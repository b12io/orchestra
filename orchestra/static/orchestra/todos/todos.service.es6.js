export default function todoApi ($http) {
  const apiBase = '/orchestra/todos/todo/'

  const listCreate = (projectId) => {
    if (projectId === undefined) {
      return apiBase
    }
    return `${apiBase}?project=${projectId}`
  }

  const details = (todoId) => `${apiBase}${todoId}/`

  //TODO(aditya): Stop using dummy response when model schema is updated.
  const dummyResponse = {
    'data': [{'id': 2410, 'created_at': '2018-06-11T21:43:38.681252Z', 'task': 14231, 'description': 'Guideline A', 'completed': false, 'skipped': true, 'start_by_datetime': null, 'due_datetime': null},
      {'id': 2411, 'created_at': '2018-06-11T21:43:38.681252Z', 'task': 14231, 'description': 'Guideline B', 'completed': false, 'skipped': true, 'start_by_datetime': null, 'due_datetime': null},
      {'id': 2412, 'created_at': '2018-06-11T21:43:38.681252Z', 'task': 14231, 'description': 'Guideline C', 'completed': false, 'skipped': true, 'start_by_datetime': null, 'due_datetime': null},
      {'id': 2413, 'created_at': '2018-06-11T21:43:38.681252Z', 'task': 14231, 'description': 'Guideline D', 'completed': false, 'skipped': false, 'start_by_datetime': null, 'due_datetime': null},
      {'id': 2414, 'created_at': '2018-06-11T21:43:38.681252Z', 'task': 14231, 'description': 'Guideline E', 'completed': false, 'skipped': false, 'start_by_datetime': null, 'due_datetime': null},
      {'id': 2415, 'created_at': '2018-06-11T21:43:38.681252Z', 'task': 14231, 'description': 'Guideline F', 'completed': false, 'skipped': false, 'start_by_datetime': null, 'due_datetime': null}]
  }
  return {
    create: (todo) => $http.post(listCreate(), todo)
      .then(response => response.data),
    list: (projectId) => $http.get(listCreate(projectId))
      .then(response => dummyResponse.data),
    update: (todo) => $http.put(details(todo.id), todo)
  }
};
