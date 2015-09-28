(function () {
  'use strict';

  angular.module('journalism_workflow.copy_editor.directives').directive(
    'copyEditor', function() {
      return {
	restrict: 'E',
	controller: 'CopyEditorController',
	scope: {
          taskAssignment: '=',
	},
	templateUrl: '/static/journalism_workflow/copy_editor/partials/copy_editor.html',
      };
    });
})();
