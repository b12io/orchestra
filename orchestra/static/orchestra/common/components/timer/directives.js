(function() {
  'use strict';

  angular
    .module('orchestra.common.components.directives')
    .directive('workTimer', workTimer);

  function workTimer() {
    return {
      restrict: 'E',
      scope: {
        taskId: '=taskId',
      },
      link: function(scope, el, attr) {
      },
      controller: workTimerController,
      controllerAs: 'vm',
      templateUrl: '/static/orchestra/common/components/timer/timer.html'
    };
  }

  function makeTwoDigits(i) {
    if (i < 10) {i = "0" + i};  // add zero in front of numbers < 10
    return i;
  }
  
  function prettyDisplayTime(milliseconds) {
    var hours = Math.floor(milliseconds / 1000 / 60 / 60);
    milliseconds = milliseconds - hours * 1000 * 3600;
    var mins = Math.floor(milliseconds / 1000 / 60);
    milliseconds = milliseconds - mins * 1000 * 60;
    var secs = Math.round(milliseconds / 1000);
    mins = makeTwoDigits(mins);
    secs = makeTwoDigits(secs);
    return hours + ":" + mins + ":" + secs;
  }

  function workTimerController($scope, $timeout) {
    var vm = this;
    vm.taskId = $scope.taskId;
    vm.displayTime = '';
    vm.timerRunning = false;

    var startTime = null;
    var timerPromise = null;

    vm.startTimer = function() {
      function updateTime() {
        var today = new Date();
        var diff = today - startTime;
        vm.displayTime = prettyDisplayTime(diff);
        if (vm.timerRunning) {
          timerPromise = $timeout(updateTime, 500);
        }
      }

      startTime = new Date();
      vm.timerRunning = true;
      updateTime();
    }

    vm.stopTimer = function() {
      $timeout.cancel(timerPromise);
      vm.timerRunning = false;
    }
  }
})();
