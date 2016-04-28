(function() {
  'use strict';

  angular.module('journalism_workflow.v1.photographer').directive(
    'photographer', function() {
      return {
        restrict: 'E',
        controller: 'ImageUploadController',
        scope: {
          taskAssignment: '=',
        },
        templateUrl: $static('/static/journalism_workflow/v1/photographer/partials/photographer.html'),
      };
    });
})();
