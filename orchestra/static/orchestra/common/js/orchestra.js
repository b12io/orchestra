(function() {
  'use strict';

  var modules = [
    'orchestra.routes', 'orchestra.config', 'orchestra.common', 'orchestra.timing',
    'orchestra.dashboard', 'orchestra.task', 'orchestra.project_management', 'orchestra.analytics'
  ];
  // Dynamically instantiate each of the angular modules from Orchestra
  // Workflow Steps
  angular.forEach(window.orchestra.angular_modules, function(module) {
    modules.push(module);
  });

  angular.module('orchestra', modules);

  angular.module('orchestra.common', []);
  angular.module('orchestra.routes', ['ngRoute']);
  angular.module('orchestra.config', []);
  angular.module('orchestra.timing', ['ui.select', 'ngSanitize', 'orchestra.common']);
  angular.module('orchestra.dashboard', ['orchestra.timing']);
  angular.module('orchestra.task', ['orchestra.timing']);
  angular.module('orchestra.project_management', ['orchestra.common']);
  angular.module('orchestra.analytics', []);

  // Dynamically instantiate each of the angular modules from Orchestra
  // Workflow Steps
  angular.forEach(window.orchestra.angular_modules, function(module) {
    angular.module(module, []);
  });

  angular.module('orchestra').run(run);

  run.$inject = ['$http', '$location', '$rootScope', '$window'];

  /**
   * @name run
   * @desc Update xsrf $http headers to align with Django's defaults
   */
  function run($http, $location, $rootScope, $window) {
    $http.defaults.xsrfHeaderName = 'X-CSRFToken';
    $http.defaults.xsrfCookieName = 'csrftoken';

    // change title based on route
    var base_title = ' | Orchestra';
    $rootScope.$on('$routeChangeSuccess', function(event, current, previous) {
      $rootScope.title = current.$$route.title + base_title;

      // Only send page views if:
      // 1) Google Analytics is on, and
      // 2) this isn't the initial pageload (analytics.html logs first page load).
      if (typeof $window.ga !== 'undefined' && typeof previous !== 'undefined') {
        $window.ga('set', {
          location: $location.absUrl(),
          title: $rootScope.title
        });
        $window.ga('send', 'pageview');
      }
    });
  }
})();
