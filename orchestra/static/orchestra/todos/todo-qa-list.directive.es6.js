import { filter } from 'lodash'
import template from './todo-qa-list.html'
import './todo-qa-list.scss'

export default function todoQaList () {
  return {
    template,
    restrict: 'E',
    scope: {
      todos: '<',
      approveTodo: '=',
      disapproveTodo: '=',
      updateTodoQaComment: '='
    },
    link: (scope, elem, attrs) => {
      scope.updatedComments = {}
      scope.onCommentChange = (todo) => {
        todo.qa.comment = todo.qa.comment.trim()
        scope.updatedComments[todo.id] = true
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

      scope.hasComment = (todo) => {
        return todo.qa && todo.qa.comment
      }

      scope.submitComment = (todo) => {
        scope.updateTodoQaComment(todo)
        scope.updatedComments[todo.id] = false
      }

      scope.addNewComment = (todo) => {
        todo.qa.comment = ' '
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
