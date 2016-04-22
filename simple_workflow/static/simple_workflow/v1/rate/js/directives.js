(function() {
  'use strict';

  angular.module('simple_workflow.v1.rate').directive(
    'rate', function() {
      return {
        restrict: 'E',
        controller: 'ImageRatingController',
        scope: {
          taskAssignment: '=',
        },
        templateUrl: $static('/static/simple_workflow/v1/rate/partials/rate.html'),
      };
    });
})();
