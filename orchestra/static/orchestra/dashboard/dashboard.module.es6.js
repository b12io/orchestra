/* global angular */

import tasktable from './tasktable.directive.es6.js'
import DashboardController from './dashboard.controller.es6.js'
import 'angular-smart-table'

const name = 'orchestra.dashboard'
angular.module(name, ['orchestra.timing', 'smart-table'])
  .directive('tasktable', tasktable)
  .controller('DashboardController', DashboardController)

export default name
