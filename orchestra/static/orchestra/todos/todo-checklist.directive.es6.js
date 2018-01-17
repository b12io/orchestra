import template from './todo-checklist.html'
import './todo-checklist.scss'

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
    }

  }
}
