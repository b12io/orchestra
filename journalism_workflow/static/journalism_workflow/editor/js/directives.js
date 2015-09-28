(function () {
  'use strict';

  angular.module('journalism_workflow.editor.directives').directive(
    'editor', function() {
      return {
	restrict: 'E',
	controller: 'StoryFormController',
	scope: {
          taskAssignment: '=',
	},
	templateUrl: '/static/journalism_workflow/editor/partials/editor.html',
      };
    });
})();
