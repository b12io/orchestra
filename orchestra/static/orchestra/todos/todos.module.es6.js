/* global angular */

import common from 'orchestra/common/common.module.es6.js'

import todoList from 'orchestra/todos/todo-list.directive.es6.js'
// import taskSelect from 'orchestra/timing/timecard/task-select/task-select.directive.es6.js'
// import enforceIntegers from 'orchestra/timing/timecard/enforce-integers.directive.es6.js'
// import TimecardController from 'orchestra/timing/timecard/timecard.controller.es6.js'
// import workTimer from 'orchestra/timing/timer/timer.directive.es6.js'
import todoApi from 'orchestra/todos/todos.service.es6.js'
// import TimeEntry from 'orchestra/timing/time-entry.service.es6.js'

const name = 'orchestra.todos'
angular.module(name, ['ui.select', 'ngSanitize', common])
  .directive('todoList', todoList)
  .factory('todoApi', todoApi)
  // .factory('Todo', Todo)
export default name

// .directive('enforceIntegers', enforceIntegers)
// .directive('workTimer', workTimer)
// .controller('TimecardController', TimecardController)
// .directive('datePicker', datePicker)
