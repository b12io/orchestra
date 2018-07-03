import { filter } from 'lodash'
import template from './todo-checklist.html'
import './todo-checklist.scss'
import 'angular-ui-tree/dist/angular-ui-tree.css'

import moment from 'moment-timezone'

export default function todoChecklist () {
  return {
    template,
    restrict: 'E',
    scope: {
      title: '@',
      todos: '<',
      templates: '<',
      recommendations: '<',
      showChecked: '=',
      showSkipped: '=',
      updateTodo: '=',
      removeTodo: '=',
      skipTodo: '=',
      unskipTodo: '=',
      steps: '<',
      taskSlugs: '<'
    },
    link: (scope, elem, attrs) => {
      scope.isNonEmptyString = (str) => {
        return str !== null && str !== undefined && str !== ''
      }

      scope.isInDanger = (todo) => {
        return (!todo.completed && moment.isBeforeNowBy(todo.due_datetime, 1, 'days')) || scope.recommendations[todo.description]
      }

      scope.isSkipped = (todo) => {
        var items = []
        if (todo.items) {
          items = filter(todo.items, scope.isSkipped)
        }
        return (todo.skipped_datetime != null && (!todo.items || todo.items.length === 0)) || items.length > 0
      }

      scope.isNotSkipped = (todo) => {
        var items = []
        if (todo.items) {
          items = filter(todo.items, scope.isNotSkipped)
        }
        return (todo.skipped_datetime == null && (!todo.items || todo.items.length === 0)) || items.length > 0
      }

      scope.filterTodoList = (todos, showSkipped) => {
        return filter(todos, showSkipped ? scope.isSkipped : scope.isNotSkipped)
      }
    }

  }
}
