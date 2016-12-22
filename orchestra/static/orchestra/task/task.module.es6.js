/* global angular */

import autoSaveTask from 'orchestra/task/autosave.service.es6.js'
import dynamicLoad from 'orchestra/task/dynamic-load.directive.es6.js'
import orchestraRequiredField from 'orchestra/task/required-field.directive.es6.js'
import requiredFields from 'orchestra/task/required-fields.service.es6.js'
import TaskController from 'orchestra/task/task.controller.es6.js'

import 'orchestra/task/task.scss'

const name = 'orchestra.task'
angular.module(name, ['orchestra.timing'])
  .controller('TaskController', TaskController)
  .directive('dynamicLoad', dynamicLoad)
  .directive('orchestraRequiredField', orchestraRequiredField)
  .factory('autoSaveTask', autoSaveTask)
  .factory('requiredFields', requiredFields)

export default name
