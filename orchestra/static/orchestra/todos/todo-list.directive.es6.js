import { reduce } from 'lodash'

import template from './todo-list.html'
import './todo-list.scss'

export default function todoList (orchestraApi) {
  'ngAnnotate'
  return {
    template,
    restrict: 'E',
    scope: {
      projectId: '='
    },
    controllerAs: 'todoList',
    bindToController: true,
    controller: function (todoApi) {
      var todoList = this
      todoList.possibleTasks = []
      todoList.newTodoTaskId = null
      todoList.newTodoDescription = null
      todoList.ready = false
      todoList.slugs = {}
      todoList.todos = []

      todoList.canAddTodo = () => {
        return todoList.newTodoTaskId && todoList.newTodoDescription
      }

      todoList.addTodo = () => {
        todoApi.create({
          task: todoList.newTodoTaskId,
          description: todoList.newTodoDescription
        }).then((taskData) => {
          todoList.todos.unshift(taskData)
          todoList.newTodoTaskId = null
          todoList.newTodoDescription = null
        })
      }

      todoList.updateTodo = (todo) => {
        todoApi.update(todo)
      }

      orchestraApi.projectInformation(todoList.projectId)
        .then((response) => {
          const humanSteps = new Set(response.data.steps.filter(step => step.is_human).map(step => step.slug))
          todoList.taskSlugs = reduce(
            Object.values(response.data.tasks), (result, task) => {
              result[task.id] = task.step_slug
              return result
            }, {})
          todoList.possibleTasks = Object.values(response.data.tasks).filter(task => task.status !== 'Complete' && humanSteps.has(task.step_slug))

          // TODO(marcua): parallelize requests rather than chaining `then`s.
          todoApi.list(todoList.projectId).then((todos) => {
            todoList.todos = todos
            todoList.ready = true
          })
        })
    }
  }
}
