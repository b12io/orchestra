/* global angular */

import common from 'orchestra/common/common.module.es6.js'

import todoList from 'orchestra/todos/todo-list.directive.es6.js'
import todoApi from 'orchestra/todos/todos.service.es6.js'

const name = 'orchestra.todos'
angular.module(name, ['ui.select', 'ngSanitize', common])
  .directive('todoList', todoList)
  .factory('todoApi', todoApi)
export default name
