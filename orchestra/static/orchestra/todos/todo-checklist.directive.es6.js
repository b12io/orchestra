import template from './todo-checklist.html'
import './todo-checklist.scss'

import moment from 'moment-timezone'

export default function todoChecklist () {
  return {
    template,
    restrict: 'E',
    scope: {
      title: '@',
      todos: '<',
      showChecked: '=',
      updateTodo: '=',
      steps: '<',
      taskSlugs: '<'
    },
    link: (scope, elem, attrs) => {
      scope.isNonEmptyString = (str) => {
        return str !== null && str !== undefined && str !== ''
      }

      scope.isInDanger = (todo) => {
        return !todo.completed && moment.isBeforeNow(todo.due_datetime, 1, 'days')
      }
    }

  }
}
