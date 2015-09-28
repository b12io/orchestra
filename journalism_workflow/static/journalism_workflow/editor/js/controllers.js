(function () {
  'use strict';

  angular
    .module('journalism_workflow.editor.controllers')
    .controller('StoryFormController', StoryFormController)

  StoryFormController.$inject = ['$scope', 'orchestraService'];

  function StoryFormController($scope, orchestraService) {
    var vm = $scope;
  }
})();
