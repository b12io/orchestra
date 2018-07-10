import { filter } from 'lodash'
import template from './todo-qa-list.html'
import './todo-qa-list.scss'

export default function todoQa () {
  return {
    template,
    restrict: 'E',
    scope: {
      todos: '<',
      approveTodo: '=',
      disapproveTodo: '=',
      updateTodoApprovalReason: '='
    },
    link: (scope, elem, attrs) => {
      scope.changedReasons = {}
      scope.reasonChanged = (todo) => {
        todo.qa.approval_reason = todo.qa.approval_reason.trim()
        scope.changedReasons[todo.id] = true
      }

      scope.isDisapproved = (todo) => {
        return todo.qa && !todo.qa.approved
      }

      scope.isApproved = (todo) => {
        return todo.qa && todo.qa.approved
      }

      scope.isApprovalPending = (todo) => {
        return !todo.qa
      }

      scope.isApprovalReasonProvided = (todo) => {
        return todo.qa && todo.qa.approval_reason
      }

      scope.submitReason = (todo) => {
        scope.updateTodoApprovalReason(todo)
        scope.changedReasons[todo.id] = false
      }

      scope.addReason = (todo) => {
        todo.qa.approval_reason = ' '
      }

      scope.isTemplateTodo = (todo) => {
        return todo.template
      }

      scope.filterTemplateTodos = (todos) => {
        return filter(todos, scope.isTemplateTodo)
      }
    }
  }
}
