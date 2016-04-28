(function() {
  'use strict';

  angular
    .module('journalism_workflow.v1.editor')
    .controller('StoryFormController', StoryFormController)

  StoryFormController.$inject = ['$scope', 'orchestraService'];

  function StoryFormController($scope, orchestraService) {
    var vm = $scope;
  }
})();
