import { defaults } from 'lodash'
import template from './qa.html'

export default function qa () {
  return {
    template,
    restrict: 'E',
    scope: {
      projectId: '=',
      taskId: '='
    },
    controllerAs: 'qa',
    bindToController: true,
    controller: function (todoApi, todoQaApi, $scope) {
      var qa = this
      qa.todos = []
      qa.ready = false

      qa.updateTodoApprovalReason = (todo) => {
        todoQaApi.update(todo.qa)
      }

      qa.approveTodo = (todo) => {
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

      qa.disapproveTodo = (todo) => {
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

      qa.transformToTree = (todos) => {
        var nodes = {}
        return todos.filter(function (obj) {
          nodes[obj.id] = defaults(obj, nodes[obj.id], { items: [] })
          obj.parent_todo && (nodes[obj.parent_todo] = (nodes[obj.parent_todo] || { items: [] }))['items'].push(obj)

          return !obj.parent_todo
        })
      }

      todoApi.list(qa.projectId).then((todos) => {
        qa.todos = qa.transformToTree(todos)
        qa.ready = true
      })
    }
  }
}
