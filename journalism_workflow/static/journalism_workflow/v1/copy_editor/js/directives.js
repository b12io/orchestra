(function () {
  'use strict';

  angular.module('journalism_workflow.v1.copy_editor.directives').directive(
    'copyEditor', function() {
      return {
	restrict: 'E',
	controller: 'CopyEditorController',
	scope: {
          taskAssignment: '=',
	},
	templateUrl: '/static/journalism_workflow/v1/copy_editor/partials/copy_editor.html',
      };
    });
})();
