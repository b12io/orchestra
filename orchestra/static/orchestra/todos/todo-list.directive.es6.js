import { reduce } from 'lodash'

import template from './todo-list.html'
import './todo-list.scss'

export default function todoList (orchestraApi) {
  'ngAnnotate'
  return {
    template,
    restrict: 'E',
    scope: {
      projectId: '=',
      taskId: '='
    },
    controllerAs: 'todoList',
    bindToController: true,
    controller: function (todoApi) {
      var todoList = this
      todoList.possibleTasks = []
      todoList.newTodoTaskId = null
      todoList.newTodoDescription = null
      todoList.ready = false
      todoList.taskSlugs = {}
      todoList.todos = []

      const createTodo = (taskId, description, completed) => todoApi.create({
        task: taskId,
        description,
        completed
      }).then((taskData) => {
        todoList.todos.unshift(taskData)
        return taskData
      })

      todoList.canAddTodo = () => {
        return todoList.newTodoTaskId && todoList.newTodoDescription
      }

      todoList.canSendToPending = () => {
        const numTodosOnThisTask = reduce(
          todoList.todos, (result, todo) => {
            return result + (todo.task === todoList.taskId ? 1 : 0)
          }, 0)
        return todoList.ready && (numTodosOnThisTask === 0)
      }

      todoList.sendToPending = () => {
        createTodo(todoList.taskId, 'Send task to pending state', true)
      }

      todoList.addTodo = () => {
        createTodo(todoList.newTodoTaskId, todoList.newTodoDescription, false)
          .then((taskData) => {
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
