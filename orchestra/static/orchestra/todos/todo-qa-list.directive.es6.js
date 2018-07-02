import { filter } from 'lodash'
import template from './todo-qa-list.html'
import './todo-qa-list.scss'

export default function todoQa () {
  return {
    template,
    restrict: 'E',
    scope: {
      title: '@',
      todos: '<',
      taskSlugs: '<',
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

      scope.isDesignTodo = (todo) => {
        return scope.taskSlugs[todo.task] === 'design' && todo.template
      }

      scope.filterDesignTodos = (todos) => {
        return filter(todos, scope.isDesignTodo)
      }
    }
  }
}
