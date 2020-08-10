import { defaults } from 'lodash'
import template from './todo-qa.html'

export default function qa (orchestraApi) {
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
      todoQa.project = null
      todoQa.ready = false

      todoQa.copyToClipboard = str => {
        const el = document.createElement('textarea')
        el.value = str
        document.body.appendChild(el)
        el.select()
        document.execCommand('copy')
        document.body.removeChild(el)
      }

      todoQa.commentSummary = (todos, summary) => {
        summary = summary || ''
        todos.forEach((todo) => {
          summary = todoQa.commentSummary(todo.items, summary)
          if (todo.qa && todo.qa.comment) {
            summary = `*Todo*: ${todo.title}\n*Comment*: ${todo.qa.comment}\n\n${summary}`
          }
        })
        return summary
      }

      todoQa.qaSummary = () => {
        const commentSummary = todoQa.commentSummary(todoQa.todos)
        if (commentSummary.length) {
          return `*Feedback on ${todoQa.project.short_description}*\n\n${commentSummary}`
        } else {
          return `*No feedback on ${todoQa.project.short_description}*`
        }
      }

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
      orchestraApi.projectInformation(todoQa.projectId)
        .then((response) => {
          const { project } = response.data[todoQa.projectId]
          todoQa.project = project
          todoApi.list(todoQa.projectId).then((todos) => {
            todoQa.todos = todoQa.transformToTree(todos)
            todoQa.ready = true
          })
        })
    }
  }
}
