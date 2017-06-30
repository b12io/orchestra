/* global angular */

import common from 'orchestra/common/common.module.es6.js'

import assignmentsVis from './assignments-vis.es6.js'
import axis from './axis.es6.js'
import crosshair from './crosshair.es6.js'
import dataService from './data-service.es6.js'
import iterationsVis from './iterations-vis.es6.js'
import projectVis from './project-vis.es6.js'
import tasksVis from './tasks-vis.es6.js'
import visUtils from './vis-utils.es6.js'
import ProjectManagementController from './project-management.controller.es6.js'

import './project-management.scss'

const name = 'orchestra.project_management'
angular.module(name, ['ui.bootstrap', 'ui.select', common])
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
