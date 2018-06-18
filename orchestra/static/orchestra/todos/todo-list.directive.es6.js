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
      todoList.list = [{
        'id': 1,
        'description': 'THINGS NOT TO DO',
        'completed': false,
        'items': [
          {
            'id': 11,
            'description': 'node1.1',
            'completed': false,
            'items': [
              {
                'id': 111,
                'description': 'node1.1.1',
                'completed': false,
                'items': []
              }
            ]
          },
          {
            'id': 12,
            'description': 'node1.2',
            'completed': false,
            'items': []
          }
        ]
      },
      {
        'id': 2,
        'description': 'GETTING STARTED',
        'completed': false,
        'items': [
          {
            'id': 21,
            'description': 'node2.1',
            'completed': false,
            'items': []
          },
          {
            'id': 22,
            'description': 'node2.2',
            'completed': false,
            'items': []
          }
        ]
      },
      {
        'id': 3,
        'description': 'ADD/UPDATE CONTENT',
        'completed': false,
        'items': [
          {
            'id': 31,
            'description': 'node3.1',
            'completed': false,
            'items': []
          }
        ]
      }]

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

      todoList.updateTodo = (todo) => {
        todoApi.update(todo)
      }

      todoList.toggleSkipTodo = (todo) => {
        if (todo.skipped_datetime) {
          todo.skipped_datetime = null
        } else {
          const datetimeUtc = moment.tz(moment(), moment.tz.guess()).utc()
          todo.skipped_datetime = datetimeUtc.format('YYYY-MM-DD HH:mm')
        }
        todoApi.update(todo)
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
