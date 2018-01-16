import { reduce } from 'lodash'
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
    controller: function (todoApi, $scope) {
      var todoList = this
      todoList.possibleTasks = []
      todoList.newTodoTaskId = null
      todoList.newTodoDescription = null
      todoList.newTodoStartDate = null
      todoList.newTodoDueDate = null
      todoList.ready = false
      todoList.taskSlugs = {}
      todoList.todos = []

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

      todoList.getLocalTime = (datetimeString) => {
        return datetimeString ? moment.utc(datetimeString).tz(moment.tz.guess()) : null
      }

      todoList.getPrettyDatetime = (datetime) => {
        return datetime.format('ddd MMMM D hh:mm a')
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

      todoList.updateTodo = (todo) => {
        todoApi.update(todo)
      }

      todoList.getDatesDisplay = (todo) => {
        const startDate = todoList.getLocalTime(todo.start_by_datetime)
        const dueDate = todoList.getLocalTime(todo.due_datetime)
        const startDateInfo = startDate ? `Start by ${todoList.getPrettyDatetime(startDate)}` : ''
        const dueDateInfo = dueDate ? `Due on ${todoList.getPrettyDatetime(dueDate)}` : ''
        return `${startDateInfo} ${dueDateInfo}`
      }

      todoList.setTimeOfDate = (datetime) => {
        $scope.$apply()
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
            todoList.todos = todos
            todoList.ready = true
          })
        })
    }
  }
}
