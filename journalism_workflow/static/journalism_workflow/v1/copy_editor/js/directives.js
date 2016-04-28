(function() {
  'use strict';

  angular.module('journalism_workflow.v1.copy_editor').directive(
    'copyEditor', function() {
      return {
        restrict: 'E',
        controller: 'CopyEditorController',
        scope: {
          taskAssignment: '=',
        },
        templateUrl: $static('/static/journalism_workflow/v1/copy_editor/partials/copy_editor.html'),
      };
    });
})();
