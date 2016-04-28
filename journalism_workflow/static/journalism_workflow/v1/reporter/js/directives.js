(function() {
  'use strict';

  angular.module('journalism_workflow.v1.reporter').directive(
    'reporter', function() {
      return {
        restrict: 'E',
        controller: 'ArticleWritingController',
        scope: {
          taskAssignment: '=',
        },
        templateUrl: $static('/static/journalism_workflow/v1/reporter/partials/reporter.html'),
      };
    });

})();
