import { defaults } from 'lodash'
import template from './todo-qa.html'

export default function qa () {
  return {
    template,
    restrict: 'E',
    scope: {
      projectId: '=',
      taskId: '='
    },
    controllerAs: 'todoQa',
    bindToController: true,
    controller: function (todoApi, todoQaApi, $scope) {
      var todoQa = this
      todoQa.todos = []
      todoQa.ready = false

      todoQa.updateTodoQaComment = (todo) => {
        todoQaApi.update(todo.qa)
      }

      todoQa.approveTodo = (todo) => {
        if (todo.qa) {
          todo.qa.approved = true
          todoQaApi.update(todo.qa)
        } else {
          todoQaApi.create({
            'todo': todo.id,
            'approved': true
          }).then((qa) => {
            todo.qa = qa
          })
        }
      }

      todoQa.disapproveTodo = (todo) => {
        if (todo.qa) {
          todo.qa.approved = false
          todoQaApi.update(todo.qa)
        } else {
          todoQaApi.create({
            'todo': todo.id,
            'approved': false
          }).then((qa) => {
            todo.qa = qa
          })
        }
      }

      todoQa.transformToTree = (todos) => {
        var nodes = {}
        return todos.filter(function (obj) {
          nodes[obj.id] = defaults(obj, nodes[obj.id], { items: [] })
          obj.parent_todo && (nodes[obj.parent_todo] = (nodes[obj.parent_todo] || { items: [] }))['items'].push(obj)

          return !obj.parent_todo
        })
      }

      todoApi.list(todoQa.projectId).then((todos) => {
        todoQa.todos = todoQa.transformToTree(todos)
        todoQa.ready = true
      })
    }
  }
}
