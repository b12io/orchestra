/* global angular */

import common from 'orchestra/common/common.module.es6.js'

import todoList from 'orchestra/todos/todo-list.directive.es6.js'
import todoQAList from 'orchestra/todos/todo-qa-list.directive.es6.js'
import todoChecklist from 'orchestra/todos/todo-checklist.directive.es6.js'
import todoApi from 'orchestra/todos/todos.service.es6.js'
import todoQAApi from 'orchestra/todos/todo-qas.service.es6.js'
import todoListTemplateApi from 'orchestra/todos/todolist-template.service.es6.js'
import 'angular-ui-tree'

const name = 'orchestra.todos'
angular.module(name, ['ui.select', 'ngSanitize', 'ui.tree', common])
  .directive('todoList', todoList)
  .directive('todoChecklist', todoChecklist)
  .directive('todoQaList', todoQAList)
  .factory('todoApi', todoApi)
  .factory('todoListTemplateApi', todoListTemplateApi)
  .factory('todoQAApi', todoQAApi)
export default name
