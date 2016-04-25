(function() {
  'use strict';

  angular
    .module('orchestra.task', [
      'orchestra.task.controllers',
      'orchestra.task.directives',
      'orchestra.task.services',
    ]);

  angular.module('orchestra.task.controllers', ['orchestra.timing']);
  angular.module('orchestra.task.directives', ['ui.bootstrap', 'orchestra.common']);
  angular.module('orchestra.task.services', []);
})();
