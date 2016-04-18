(function() {
  // 'use strict';

  angular
    .module('orchestra.common')
    .directive('workTimer', function() {
      return {
        restrict: 'E',
        scope: {
          taskId: '=taskId',
        },
        link: function(scope, el, attr) {
        },
        controller: workTimerController,
        bindToController: true,
        controllerAs: 'workTimer',
        templateUrl: '/static/orchestra/common/components/timer/timer.html'
      };
    });

  function workTimerController($http, $location, $scope, $timeout, timecardService) {
    // var workTimer = this;
    workTimer = this;

    workTimer.popoverTemplate = '/static/orchestra/common/components/timer/popover.html';
    workTimer.timecardService = timecardService;

    var resetTimer = function() {
      workTimer.timerRunning = false;
      workTimer.workDescription = '';
      workTimer.timeElapsed = moment.duration();
    };

    workTimer.toggleTimer = function() {
      if (workTimer.toggledOn) {
        workTimer.startTimer();
      }
      else {
        workTimer.stopTimer();
      }
    };

    var getInitialTimer = function() {
      var getTimerUrl = '/orchestra/api/interface/timer/';
      $http.get(getTimerUrl)
      .then(function(response) {
        if (response.data) {
          workTimer.startTime = moment().subtract(moment.duration(response.data));
          workTimer.toggledOn = true;
          workTimer.timerRunning = true;
          workTimer.updateTime();
        }
      }, function() {
        alert('Could not get timer.');
      });
    };

    workTimer.updateTime = function() {
      var currentTime = moment();
      workTimer.timeElapsed = moment.duration(currentTime - workTimer.startTime);
      if (workTimer.timerRunning) {
        workTimer.timerPromise = $timeout(workTimer.updateTime, 500);
      }
    };

    workTimer.startTimer = function() {
      var startTimerUrl = '/orchestra/api/interface/timer/start/';
      $http.post(startTimerUrl, {
        // assignment: workTimer.assignment,
      })
      .then(function(response) {
        console.log(response.data);
        workTimer.toggledOn = true;
        workTimer.startTime = moment();
        workTimer.timerRunning = true ;
        workTimer.updateTime();
      }, function() {
        alert('Could not start timer');
      });
    };

    workTimer.stopTimer = function() {
      var stopTimerUrl = '/orchestra/api/interface/timer/stop/';
      $timeout.cancel(workTimer.timerPromise);
      $http.post(stopTimerUrl, {
        description: workTimer.workDescription,
      })
      .then(function(response) {
        console.log(response.data);
        workTimer.toggledOn = false;
        timecardService.addEntry(response.data);
        resetTimer();
      }, function() {
          alert('Could not stop timer');
      });
    };

    workTimer.viewTimecard = function() {
      $location.path('/timecard');
    };

    resetTimer();
    getInitialTimer();
  }
})();
