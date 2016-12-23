/* global $static */

import moment from 'moment-timezone'

import template from './timer.html'
import './timer.scss'

export default function workTimer ($rootScope) {
  'ngAnnotate'
  return {
    template,
    restrict: 'E',
    bindToController: true,
    controllerAs: 'workTimer',
    controller: function ($http, $location, $scope, $timeout, orchestraTasks, timeEntries) {
      var workTimer = this

      // TODO(jrbotros): remove this $static call
      workTimer.popoverTemplate = $static('/static/orchestra/timing/timer/popover.html')
      workTimer.timeEntries = timeEntries

      var resetTimer = function () {
        workTimer.toggledOn = false
        workTimer.timerRunning = false
        workTimer.description = undefined
        workTimer.timeElapsed = moment.duration()
        workTimer.task = undefined
      }

      workTimer.toggleTimer = function () {
        if (workTimer.toggledOn) {
          workTimer.startTimer()
        } else {
          workTimer.stopTimer()
        }
      }

      var getInitialTimer = function () {
        var getTimerUrl = '/orchestra/api/interface/timer/'
        $http.get(getTimerUrl)
        .then(function (response) {
          if (response.data.time_worked) {
            var workTime = moment.duration(response.data.time_worked)
            workTimer.startTime = moment().subtract(workTime)
            workTimer.toggledOn = true
            workTimer.timerRunning = true
            workTimer.description = response.data.description
            orchestraTasks.data.then(function () {
              workTimer.task = orchestraTasks.tasksByAssignmentId[response.data.assignment]
            })
            workTimer.updateTime()
          }
        }, function () {
          window.alert('Could not get timer.')
        })
      }

      workTimer.updateTime = function () {
        var currentTime = moment()
        workTimer.timeElapsed = moment.duration(currentTime - workTimer.startTime)
        if (workTimer.timerRunning) {
          workTimer.timerPromise = $timeout(workTimer.updateTime, 500)
        }
      }

      workTimer.startTimer = function () {
        var startTimerUrl = '/orchestra/api/interface/timer/start/'
        var assignmentId = workTimer.task ? workTimer.task.assignment_id : null
        $http.post(startTimerUrl, {
          assignment: assignmentId
        })
        .then(function (response) {
          workTimer.task = orchestraTasks.currentTask
          workTimer.timerRunning = true
          workTimer.toggledOn = true
          workTimer.startTime = moment()
          workTimer.updateTime()
        }, function () {
          window.alert('Could not start timer')
        })
      }

      workTimer.stopTimer = function () {
        var stopTimerUrl = '/orchestra/api/interface/timer/stop/'
        $timeout.cancel(workTimer.timerPromise)
        $http.post(stopTimerUrl)
        .then(function (response) {
          var entry = timeEntries.addEntry(response.data)
          resetTimer()
          if (entry.isIncomplete()) {
            if (window.confirm('Your new time entry is missing a description or assignment. Would you like to view your timecard and edit it there?')) {
              workTimer.viewTimecard()
            }
          }
        }, function () {
          window.alert('Could not stop timer')
        })
      }

      workTimer.updateTimer = function () {
        var url = '/orchestra/api/interface/timer/update/'
        var assignmentId = workTimer.task ? workTimer.task.assignment_id : null
        var data = {
          assignment: assignmentId,
          description: workTimer.description
        }
        $http.post(url, data)
        .catch(function () {
          window.alert('Could not update timer description')
        })
      }

      $scope.$watch('workTimer.task', function (newVal, oldVal) {
        if (newVal !== oldVal && workTimer.timerRunning) {
          workTimer.updateTimer()
        }
      })

      workTimer.viewTimecard = function () {
        $location.path('/timecard')
      }

      resetTimer()
      getInitialTimer()
    }
  }
}
