(function() {
  'use strict';

  angular.module('orchestra.timing')
    .controller('TimecardController', function($routeParams, $scope, orchestraTasks, timeEntries) {
      var vm = this;
      vm.taskId = $routeParams.taskId;

      vm.orchestraTasks = orchestraTasks;
      vm.timeEntries = timeEntries;

      vm.datetimeFromKey = function(entries) {
        if (entries.$key) {
          return moment(entries.$key);
        }
      };

      vm.prettyDate = function(dateString) {
        // TODO(jrbotros): fix groupby with custom comparator
        if (dateString) {
          return moment(dateString).format('MMMM D');
        }
      };

      vm.editEntry = function(entry) {
        entry.editData = vm.initialEditData(entry);
        entry.editing = !entry.editing;
      };

      vm.saveChanges = function(entry) {
        if (vm.entryUnchanged(entry)) {
          vm.cancelChanges();
          return;
        }
        entry.description = entry.editData.description;
        entry.time_worked = moment.duration(entry.editData.timeWorked);
        entry.assignment = entry.editData.task.assignment_id;
        entry.save();
        entry.editing = false;
        entry.editData = vm.initialEditData(entry);
      };

      vm.cancelChanges = function(entry) {
        entry.editing = false;
        entry.editData = vm.initialEditData(entry);
      };

      vm.initialEditData = function(entry) {
        var data = {
          description: entry.description,
          // Time worked should only include hours and minutes, and should be
          // rounded up to the minute
          timeWorked: entry.time_worked.roundMinute().componentize(),
          task: orchestraTasks.tasksByAssignmentId[entry.assignment]
        };
        // Don't set task if tasks haven't loaded yet
        if (orchestraTasks.tasksByAssignmentId) {
          data.task = orchestraTasks.tasksByAssignmentId[entry.assignment];
        }
      };

      // When tasks load, add correct task to any entry being edited
      orchestraTasks.data.then(function() {
        timeEntries.data.then(function() {
          timeEntries.entries.forEach(function(entry) {
            if (entry.editData) {
              entry.editData.task = orchestraTasks.tasksByAssignmentId[entry.assignment];
            }
          });
        });
      });


      vm.entryUnchanged = function(entry) {
        return angular.equals(entry.editData, vm.initialEditData(entry));
      };

      vm.editingEntries = function() {
        for (var i = 0; i < timeEntries.entries.length; i++) {
          if (timeEntries.entries[i].editing === true) {
            return true;
          }
        }
        return false;
      };

      vm.resetEntries = function() {
        timeEntries.entries.forEach(function(entry) {
          delete entry.editing;
          delete entry.editData;
        });
      };

      var warningString = "Your latest changes haven't been saved.";
      var defaultPrompt = 'Are you sure you want to leave the page?';

      var beforeUnloadListener = function(event) {
        if (vm.editingEntries()) {
          event.returnValue = warningString;
        }
      };

      // Browser close or reload
      window.addEventListener('beforeunload', beforeUnloadListener);

      // Angular location change
      $scope.$on('$locationChangeStart', function(e) {
        if (vm.editingEntries()) {
          if (confirm(warningString + '\n' + defaultPrompt)) {
            vm.resetEntries();

            // Disable confirm dialog if navigating away from view.
            window.removeEventListener('beforeunload', beforeUnloadListener);
          }
          else {
            e.preventDefault();
          }
        }
      });
    });
})();
