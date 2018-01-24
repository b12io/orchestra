/* global angular */

import {
  isUndefined
} from 'lodash'

import common from 'orchestra/common/common.module.es6.js'
import dashboard from 'orchestra/dashboard/dashboard.module.es6.js'
import projectManagement from 'orchestra/project-management/project-management.module.es6.js'
import task from 'orchestra/task/task.module.es6.js'
import timing from 'orchestra/timing/timing.module.es6.js'
import todos from 'orchestra/todos/todos.module.es6.js'
import teamInfo from 'orchestra/team-info/team-info.module.es6.js'

import config from 'orchestra/config.es6.js'

angular.module('orchestra.analytics', [])

// Include any custom workflow modules as dependencies
window.orchestra.angular_modules.forEach(module => angular.module(module, []))
angular.module('orchestra.workflows', window.orchestra.angular_modules)

angular
  .module('orchestra', [
    'ngRoute', common, timing, dashboard, task, todos, teamInfo,
    projectManagement, 'orchestra.analytics', 'orchestra.workflows'
  ])
  .config(config)
  .run(($http, $location, $rootScope, $window) => {
    'ngAnnotate'

    // Update xsrf $http headers to align with Django's defaults
    $http.defaults.xsrfHeaderName = 'X-CSRFToken'
    $http.defaults.xsrfCookieName = 'csrftoken'

    // Change title based on route
    var baseTitle = ' | Orchestra'
    $rootScope.$on('$routeChangeSuccess', function (event, current, previous) {
      $rootScope.title = current.$$route.title + baseTitle

      // Only send page views if:
      // 1) Google Analytics is on, and
      // 2) this isn't the initial pageload (analytics.html logs first page load).
      if (!isUndefined($window.ga) && !isUndefined(previous)) {
        $window.ga('set', {
          location: $location.absUrl(),
          title: $rootScope.title
        })
        $window.ga('send', 'pageview')
      }
    })
  })
