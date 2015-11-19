(function () {
  'use strict';

  angular.module('journalism_workflow.v1.photographer.directives').directive(
    'photographer', function() {
      return {
	restrict: 'E',
	controller: 'ImageUploadController',
	scope: {
          taskAssignment: '=',
	},
	templateUrl: '/static/journalism_workflow/v1/photographer/partials/photographer.html',
      };
    });
})();
