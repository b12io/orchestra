(function () {
  'use strict';

  angular
    .module('simple_workflow.rate.controllers')
    .controller('ImageRatingController', ImageRatingController)

  ImageRatingController.$inject = ['$scope', 'orchestraService'];

  function ImageRatingController($scope, orchestraService) {
    var vm = $scope;
    var crawlStep = orchestraService.taskUtils.findPrerequisite(
      vm.taskAssignment, 'crawl');
    if (crawlStep.task.data.status !== 'success') {
      vm.imageURL = "http://media.giphy.com/media/2vA33ikUb0Qz6/giphy.gif";
      vm.success = false;
    } else {
      vm.imageURL = crawlStep.task.data.image;
      vm.success = true;
    }
  }
})();
