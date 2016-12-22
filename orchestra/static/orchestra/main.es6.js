/* global angular */

import {
  isUndefined
} from 'lodash'

import common from 'orchestra/common/common.module.es6.js'
import config from 'orchestra/config.es6.js'

angular.module('orchestra.timing', ['ui.select', 'ngSanitize', common])
angular.module('orchestra.dashboard', ['orchestra.timing'])
angular.module('orchestra.task', ['orchestra.timing'])
angular.module('orchestra.project_management', ['ui.select', common])
angular.module('orchestra.analytics', [])

window.orchestra.angular_modules.forEach(module => {
  angular.module(module, [])
})

// TODO(jrbotros): pare down these modules
angular
  .module('orchestra', [
    'ngRoute', common, 'orchestra.timing', 'orchestra.dashboard',
    'orchestra.task', 'orchestra.project_management', 'orchestra.analytics',
    // Include angular modules from Orchestra workflow steps
    ...window.orchestra.angular_modules
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
