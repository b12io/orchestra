(function() {
  'use strict';

  angular.module('orchestra.dashboard', [
    'orchestra.dashboard.controllers',
    'orchestra.dashboard.directives'
  ]);

  angular.module('orchestra.dashboard.controllers', [
    'orchestra.common.services'
  ]);
  angular.module('orchestra.dashboard.directives', []);
})();
