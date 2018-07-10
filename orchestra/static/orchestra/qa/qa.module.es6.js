/* global angular */

import common from 'orchestra/common/common.module.es6.js'

import qa from 'orchestra/qa/qa.directive.es6.js'
import todoQaList from 'orchestra/qa/todo-qa-list.directive.es6.js'
import todoApi from 'orchestra/todos/todos.service.es6.js'
import todoQaApi from 'orchestra/qa/todo-qas.service.es6.js'
import 'angular-ui-tree'

const name = 'orchestra.qa'
angular.module(name, ['ngSanitize', 'ui.tree', common])
  .directive('qa', qa)
  .directive('todoQaList', todoQaList)
  .factory('todoApi', todoApi)
  .factory('todoQaApi', todoQaApi)
export default name
