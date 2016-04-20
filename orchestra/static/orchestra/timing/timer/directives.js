(function() {
  'use strict';

  angular
    .module('orchestra.timing')
    .directive('workTimer', function() {
      return {
        restrict: 'E',
        scope: {
          taskId: '=taskId',
        },
        bindToController: true,
        controllerAs: 'workTimer',
        templateUrl: $static('/static/orchestra/timing/timer/timer.html'),
        controller: function($http, $location, $scope, $timeout, timeEntries) {
          var workTimer = this;

          workTimer.popoverTemplate = $static('/static/orchestra/timing/timer/popover.html');

          var resetTimer = function() {
            workTimer.toggledOn = false;
            workTimer.timerRunning = false;
            workTimer.description = undefined;
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
                var workTime = moment.duration(response.data.time_worked);
                workTimer.startTime = moment().subtract(workTime);
                workTimer.toggledOn = true;
                workTimer.timerRunning = true;
                workTimer.description = response.data.description;
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
              // TODO(jrbotros): add current assignment here
            })
            .then(function(response) {
              workTimer.timerRunning = true ;
              workTimer.toggledOn = true;
              workTimer.startTime = moment();
              workTimer.updateTime();
            }, function() {
              alert('Could not start timer');
            });
          };

          workTimer.stopTimer = function() {
            var stopTimerUrl = '/orchestra/api/interface/timer/stop/';
            $timeout.cancel(workTimer.timerPromise);
            $http.post(stopTimerUrl)
            .then(function(response) {
              timeEntries.addEntry(response.data);
              resetTimer();
            }, function() {
                alert('Could not stop timer');
            });
          };

          workTimer.updateDescription = function() {
            var url = '/orchestra/api/interface/timer/description/';
            $http.post(url, {
              description: workTimer.description,
            })
            .catch(function() {
                alert('Could not update timer description');
            });
          };

          resetTimer();
          getInitialTimer();
        }
      };
    });
})();
