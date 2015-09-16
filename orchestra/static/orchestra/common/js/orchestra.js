(function () {
  'use strict';

  var modules = ['orchestra.routes', 'orchestra.config', 'orchestra.dashboard',
                 'orchestra.task', 'orchestra.common'];
  // Dynamically instantiate each of the angular modules from Orchestra
  // Workflow Steps
  angular.forEach(window.orchestra.angular_modules, function(module) {
    modules.push(module);
  })

  angular.module('orchestra', modules);

  angular.module('orchestra.routes', ['ngRoute']);
  angular.module('orchestra.config', []);
  angular.module('orchestra.dashboard', []);
  angular.module('orchestra.task', []);
  angular.module('orchestra.common', []);

  // Dynamically instantiate each of the angular modules from Orchestra
  // Workflow Steps
  angular.forEach(window.orchestra.angular_modules, function(module) {
    angular.module(module, []);
   })

  angular.module('orchestra').run(run);

  run.$inject = ['$http', '$location', '$rootScope'];

  /**
  * @name run
  * @desc Update xsrf $http headers to align with Django's defaults
  */
  function run($http, $location, $rootScope) {
    $http.defaults.xsrfHeaderName = 'X-CSRFToken';
    $http.defaults.xsrfCookieName = 'csrftoken';

    // change title based on route
    var base_title = ' | Orchestra'
    $rootScope.$on('$routeChangeSuccess', function (event, current, previous) {
      $rootScope.title = current.$$route.title + base_title;
    });
  }
})();
