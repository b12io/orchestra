/* global angular */

import taskcards from './taskcards.directive.es6.js'
import DashboardController from './dashboard.controller.es6.js'

const name = 'orchestra.dashboard'
angular.module(name, ['orchestra.timing'])
  .directive('taskcards', taskcards)
  .controller('DashboardController', DashboardController)

export default name
