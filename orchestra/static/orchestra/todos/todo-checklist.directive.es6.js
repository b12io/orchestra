import { filter } from 'lodash'
import template from './todo-checklist.html'
import './todo-checklist.scss'
import 'angular-ui-tree/dist/angular-ui-tree.css'

import moment from 'moment-timezone'
import {
  PENDING_STATUS,
  COMPLETED_STATUS,
  DECLINED_STATUS
} from './constants.es6.js'

export default function todoChecklist () {
  return {
    template,
    restrict: 'E',
    scope: {
      title: '@',
      todos: '<',
      templates: '<',
      todoQas: '<',
      showChecked: '=',
      showSkipped: '=',
      updateTodo: '=',
      removeTodo: '=',
      skipTodo: '=',
      unskipTodo: '=',
      onToggleTodo: '=',
      steps: '<'
    },
    link: (scope, elem, attrs) => {
      scope.COMPLETED_STATUS = COMPLETED_STATUS

      scope.isNonEmptyString = (str) => {
        return str !== null && str !== undefined && str !== ''
      }

      scope.toggleTodo = (todo, todoNodeScope) => {
        todoNodeScope.toggle()
        scope.onToggleTodo(todo, todoNodeScope.collapsed)
      }

      scope.isInDanger = (todo) => {
        return (todo.status === PENDING_STATUS && moment.isBeforeNowBy(todo.due_datetime, 1, 'days')) || (scope.todoQas[todo.title] && scope.todoQas[todo.title].approved === false)
      }

      scope.isSkipped = (todo) => {
        var items = []
        if (todo.items) {
          items = filter(todo.items, scope.isSkipped)
        }
        return (todo.status === DECLINED_STATUS && (!todo.items || todo.items.length === 0)) || items.length > 0
      }

      scope.isNotSkipped = (todo) => {
        var items = []
        if (todo.items) {
          items = filter(todo.items, scope.isNotSkipped)
        }
        return (todo.status !== DECLINED_STATUS && (!todo.items || todo.items.length === 0)) || items.length > 0
      }

      scope.isCollapsed = (todo, showSkipped) => {
        var items = []
        if (todo.items) {
          items = filter(todo.items, (todo) => {
            return scope.hasTodoQaComment(todo, showSkipped)
          })
        }
        return items.length === 0
      }

      scope.hasTodoQaComment = (todo, showSkipped) => {
        var items = []
        if (todo.items) {
          items = filter(todo.items, (todo) => {
            return scope.hasTodoQaComment(todo, showSkipped)
          })
        }
        return ((scope.todoQas[todo.title] && scope.todoQas[todo.title].comment) && (showSkipped ? scope.isSkipped(todo) : scope.isNotSkipped(todo))) || items.length !== 0
      }

      scope.filterTodoList = (todos, showSkipped) => {
        return filter(todos, showSkipped ? scope.isSkipped : scope.isNotSkipped)
      }
    }

  }
}
