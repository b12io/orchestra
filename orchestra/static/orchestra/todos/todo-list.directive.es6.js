import { reduce, defaults } from 'lodash'
import template from './todo-list.html'
import moment from 'moment-timezone'
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
    controller: function (todoApi, todoListTemplateApi, todoQaApi, $scope) {
      var todoList = this
      todoList.possibleTasks = []
      todoList.newTodoTaskId = null
      todoList.newTodoDescription = null
      todoList.newTodoStartDate = null
      todoList.newTodoDueDate = null
      todoList.ready = false
      todoList.taskSlugs = {}
      todoList.todos = []
      todoList.templates = []
      todoList.todoQas = []

      const createTodo = (taskId, description, completed, startDate, dueDate) => todoApi.create({
        task: taskId,
        description,
        completed,
        start_by_datetime: startDate,
        due_datetime: dueDate
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

      todoList.getUTCDateTimeString = (datetime) => {
        if (!datetime) {
          return null
        }
        const datetimeUtc = moment.tz(datetime.format('YYYY-MM-DD HH:mm'), moment.tz.guess()).utc()
        return datetimeUtc.format('YYYY-MM-DD HH:mm')
      }

      todoList.addTodo = () => {
        const start = todoList.getUTCDateTimeString(todoList.newTodoStartDate)
        const due = todoList.getUTCDateTimeString(todoList.newTodoDueDate)

        createTodo(todoList.newTodoTaskId,
          todoList.newTodoDescription,
          false,
          start,
          due
        ).then((taskData) => {
          todoList.newTodoDescription = null
          todoList.newTodoStartDate = null
          todoList.newTodoDueDate = null
        })
      }

      todoList.updateTodoListFromTemplate = (newTodoListTemplateSlug) => {
        todoListTemplateApi.updateTodoListFromTemplate({
          task: todoList.newTodoTaskId,
          todolist_template: newTodoListTemplateSlug
        }).then((updatedTodos) => {
          todoList.newTodoListTemplateSlug = null
          todoList.todos = todoList.transformToTree(updatedTodos)
        })
      }

      todoList.updateTodo = (todo) => {
        todoApi.update(todo)
      }

      todoList.removeTodo = (todo) => {
        var index = todoList.todos.indexOf(todo)
        todoList.todos.splice(index, 1)
        todoApi.delete(todo)
      }

      todoList.skipTodo = (todo) => {
        const datetimeUtc = moment.tz(moment(), moment.tz.guess()).utc()
        todo.skipped_datetime = datetimeUtc.format('YYYY-MM-DD HH:mm')
        if (todo.items) {
          todo.items.forEach(todoList.skipTodo)
        }
        todoApi.update(todo)
      }

      todoList.unskipTodo = (todo) => {
        todo.skipped_datetime = null
        if (todo.items) {
          todo.items.forEach(todoList.unskipTodo)
        }
        todoApi.update(todo)
      }

      todoList.setTimeOfDate = (datetime) => {
        $scope.$apply()
      }

      todoList.transformToTree = (todos) => {
        var nodes = {}
        return todos.filter(function (obj) {
          nodes[obj.id] = defaults(obj, nodes[obj.id], { items: [] })
          obj.parent_todo && (nodes[obj.parent_todo] = (nodes[obj.parent_todo] || { items: [] }))['items'].push(obj)

          return !obj.parent_todo
        })
      }

      orchestraApi.projectInformation(todoList.projectId)
        .then((response) => {
          const humanSteps = new Set(response.data.steps.filter(step => step.is_human).map(step => step.slug))
          todoList.steps = reduce(
            Object.values(response.data.steps), (result, step) => {
              result[step.slug] = step
              return result
            }, {})
          todoList.taskSlugs = reduce(
            Object.values(response.data.tasks), (result, task) => {
              result[task.id] = task.step_slug
              return result
            }, {})
          todoList.possibleTasks = Object.values(response.data.tasks).filter(task => task.status !== 'Complete' && humanSteps.has(task.step_slug))

          // TODO(marcua): parallelize requests rather than chaining `then`s.
          todoApi.list(todoList.projectId).then((todos) => {
            todoListTemplateApi.list().then((templates) => {
              todoQaApi.workerRecentTodoQas(todoList.projectId).then((todoQas) => {
                todoList.todoQas = todoQas
                todoList.templates = templates
                todoList.todos = todoList.transformToTree(todos)
                todoList.ready = true
              })
            })
          })
        })
    }
  }
}
