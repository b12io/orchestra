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
      todoList.newTodoStepSlug = null
      todoList.newTodoDescription = null
      todoList.newTodoStartDate = null
      todoList.newTodoDueDate = null
      todoList.ready = false
      todoList.todos = []
      todoList.templates = []
      todoList.todoQas = []

      const createTodo = (title, completed, startDate, dueDate) => {
        todoApi.create({
          project: todoList.projectId,
          step: todoList.newTodoStepSlug,
          title,
          completed,
          start_by_datetime: startDate,
          due_datetime: dueDate
        }).then((taskData) => {
          todoList.todos.unshift(taskData)
          // Reset form
          todoList.newTodoStepSlug = null
          todoList.newTodoDescription = null
          todoList.newTodoStartDate = null
          todoList.newTodoDueDate = null
          return taskData
        })
      }

      todoList.canAddTodo = () => {
        return todoList.newTodoStepSlug && todoList.newTodoDescription
      }

      todoList.getUTCDateTimeString = (datetime) => {
        if (!datetime) {
          return null
        }
        const datetimeUtc = moment.tz(datetime.format('YYYY-MM-DD HH:mm:ss'), moment.tz.guess()).utc()
        return datetimeUtc.format('YYYY-MM-DD HH:mm:ss')
      }

      todoList.addTodo = () => {
        const start = todoList.getUTCDateTimeString(todoList.newTodoStartDate)
        const due = todoList.getUTCDateTimeString(todoList.newTodoDueDate)

        createTodo(todoList.newTodoDescription,
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
          project: todoList.projectId,
          step: todoList.newTodoStepSlug,
          todolist_template: newTodoListTemplateSlug
        }).then((updatedTodos) => {
          todoList.newTodoListTemplateSlug = null
          todoList.todos = todoList.transformToTree(updatedTodos)
        })
      }

      todoList.updateTodo = (todo) => {
        todoList.addActionToTodoActivityLog(todo, todo.completed ? 'complete' : 'incomplete')
        todoApi.update(todo)
      }

      todoList.removeTodo = (todo) => {
        var index = todoList.todos.indexOf(todo)
        todoList.todos.splice(index, 1)
        todoApi.delete(todo)
      }

      todoList.addActionToTodoActivityLog = (todo, action, datetime) => {
        const activityDatetime = datetime || todoList.getUTCDateTimeString(moment())
        var activityLog = JSON.parse(todo.activity_log.replace(/'/g, '"'))
        activityLog['actions'].push({
          'action': action,
          'datetime': activityDatetime,
          'step_slug': todo.step
        })
        todo.activity_log = JSON.stringify(activityLog).replace(/'/g, '"')
      }

      todoList.onToggleTodo = (todo, collapsed) => {
        todoList.addActionToTodoActivityLog(todo, collapsed ? 'collapse' : 'expand')
        todoApi.update(todo)
      }

      todoList.skipTodo = (todo) => {
        todo.skipped_datetime = todoList.getUTCDateTimeString(moment())
        todoList.addActionToTodoActivityLog(todo, 'skip', todo.skipped_datetime)
        if (todo.items) {
          todo.items.forEach(todoList.skipTodo)
        }
        todoApi.update(todo)
      }

      todoList.unskipTodo = (todo) => {
        todo.skipped_datetime = null
        todoList.addActionToTodoActivityLog(todo, 'unskip')
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
          const data = response.data[todoList.projectId]
          const {steps, tasks} = data
          const humanSteps = new Set(steps.filter(step => step.is_human).map(step => step.slug))
          todoList.steps = reduce(
            Object.values(steps), (result, step) => {
              result[step.slug] = step
              return result
            }, {})
          todoList.possibleTasks = Object.values(tasks).filter(task => task.status !== 'Complete' && humanSteps.has(task.step_slug))

          const p1 = todoListTemplateApi.list()
          const p2 = todoQaApi.workerTaskRecentTodoQas(todoList.taskId)
          const p3 = todoApi.list(todoList.projectId)
          Promise.all([p1, p2, p3]).then(([templates, todoQas, todos]) => {
            todoList.templates = templates
            todoList.todoQas = todoQas
            todoList.todos = todoList.transformToTree(todos)
            todoList.ready = true
            $scope.$apply()
          })
        })
    }
  }
}
