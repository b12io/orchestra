(function() {
  'use strict';

  angular.module('journalism_workflow.v1.editor').directive(
    'editor', function() {
      return {
        restrict: 'E',
        controller: 'StoryFormController',
        scope: {
          taskAssignment: '=',
        },
        templateUrl: $static('/static/journalism_workflow/v1/editor/partials/editor.html'),
      };
    });
})();
