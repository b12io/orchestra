(function () {
  'use strict';

  angular.module('simple_workflow.rate.directives').directive(
    'rate', function() {
      return {
	restrict: 'E',
	controller: 'ImageRatingController',
	scope: {
          taskAssignment: '=',
	},
	templateUrl: '/static/simple_workflow/rate/partials/rate.html',
      };
    });
})();
