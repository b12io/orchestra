(function () {
  'use strict';

  angular.module('simple_workflow.v1.rate.directives').directive(
    'rate', function() {
      return {
	restrict: 'E',
	controller: 'ImageRatingController',
	scope: {
          taskAssignment: '=',
	},
	templateUrl: '/static/simple_workflow/v1/rate/partials/rate.html',
      };
    });
})();
