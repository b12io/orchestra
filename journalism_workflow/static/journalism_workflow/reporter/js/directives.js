(function () {
  'use strict';

  angular.module('journalism_workflow.reporter.directives').directive(
    'reporter', function() {
      return {
	restrict: 'E',
	controller: 'ArticleWritingController',
	scope: {
          taskAssignment: '=',
	},
	templateUrl: '/static/journalism_workflow/reporter/partials/reporter.html',
      };
    });

})();
