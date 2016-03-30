(function() {
  'use strict';

  angular
    .module('orchestra.task', [
      'orchestra.task.controllers',
      'orchestra.task.directives',
      'orchestra.task.services',
    ]);

  angular.module('orchestra.task.controllers', []);
  angular.module('orchestra.task.directives', ['ui.bootstrap', 'angular-capitalize-filter']);
  angular.module('orchestra.task.services', []);
})();
