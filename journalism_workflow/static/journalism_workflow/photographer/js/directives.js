(function () {
  'use strict';

  angular.module('journalism_workflow.photographer.directives').directive(
    'photographer', function() {
      return {
	restrict: 'E',
	controller: 'ImageUploadController',
	scope: {
          taskAssignment: '=',
	},
	templateUrl: '/static/journalism_workflow/photographer/partials/photographer.html',
      };
    });
})();
