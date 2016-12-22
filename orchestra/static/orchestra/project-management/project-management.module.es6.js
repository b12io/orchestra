/* global angular */

import common from 'orchestra/common/common.module.es6.js'

import ProjectManagementController from './project-management.controller.es6.js'
import assignmentsVis from './js/assignments-vis.es6.js'
import axis from './js/axis.es6.js'
import crosshair from './js/crosshair.es6.js'
import dataService from './js/data-service.es6.js'
import iterationsVis from './js/iterations-vis.es6.js'
import projectVis from './js/project-vis.es6.js'
import tasksVis from './js/tasks-vis.es6.js'
import visUtils from './js/vis-utils.es6.js'

import './project-management.scss'

const name = 'orchestra.project_management'
angular.module(name, ['ui.select', common])
  .controller('ProjectManagementController', ProjectManagementController)
  .factory('assignmentsVis', assignmentsVis)
  .factory('axis', axis)
  .factory('crosshair', crosshair)
  .factory('dataService', dataService)
  .factory('iterationsVis', iterationsVis)
  .factory('projectVis', projectVis)
  .factory('tasksVis', tasksVis)
  .factory('visUtils', visUtils)

export default name
