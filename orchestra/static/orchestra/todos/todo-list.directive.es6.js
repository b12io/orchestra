import { reduce } from 'lodash'
// import moment from 'moment-timezone'
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
      todoList.tmpTime = null// moment()

      const createTodo = (taskId, description, completed, startDate, dueDate) => todoApi.create({
        task: taskId,
        description,
        completed,
        start_date: startDate,
        due_date: dueDate
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

      todoList.getDateString = (datetime) => {
        return datetime ? datetime.format('YYYY-MM-DD') : null
      }

      todoList.addTodo = () => {
        const startDate = todoList.getDateString(todoList.newTodoStartDate)
        const dueDate = todoList.getDateString(todoList.newTodoDueDate)
        console.log(todoList.newTodoStartDate.format('YYYY-MM-DD HH:mm z'), todoList.newTodoDueDate.format('YYYY-MM-DD HH:mm z'))
        createTodo(todoList.newTodoTaskId,
          todoList.newTodoDescription,
          false,
          startDate,
          dueDate
        ).then((taskData) => {
          todoList.newTodoDescription = null
        })
      }

      todoList.updateTodo = (todo) => {
        todoApi.update(todo)
      }

      todoList.datesDisplay = (todo) => {
        // console.log(todo)
        return todo.due_date ? `Due on ${todo.due_date}` : ''
      }

      todoList.setTimeOfDate = (datetime) => {
        // console.log(datetime, datetime.hours(), datetime.minutes())
        if (!datetime.hours()) {
          datetime.hours(18)
        }
        $scope.$apply()
      }

      // TODO(paopow) : delete this and uncomment in the original place
      todoApi.list(todoList.projectId).then((todos) => {
        // console.log(todos)
        todoList.todos = todos
        todoList.ready = true
      })

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
          // todoApi.list(todoList.projectId).then((todos) => {
          //   console.log(todos)
          //   todoList.todos = todos
          //   todoList.ready = true
          // })
        })
    }
  }
}
