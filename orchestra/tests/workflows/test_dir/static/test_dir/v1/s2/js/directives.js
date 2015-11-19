(function () {
  'use strict';

  angular.module('test_dir.v1.s2.directives').directive(
    's2', function() {
      return {
	restrict: 'E',
	controller: 'S2Controller',
	scope: {
          taskAssignment: '=',
	},
	templateUrl: '/static/test_dir/v1/s2/partials/s2.html',
      };
    });
})();
