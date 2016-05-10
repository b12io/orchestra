(function() {
  // 'use strict';

  angular.module('orchestra.timing')
    .controller('TimecardController', function($routeParams, $scope, orchestraTasks, timeEntries) {
      // var vm = this;
      vm = this;
      vm.taskId = $routeParams.taskId;

      vm.orchestraTasks = orchestraTasks;
      vm.timeEntries = timeEntries;

      vm.weekStart = moment().startOf('isoweek');
      vm.weekEnd = moment().endOf('isoweek');

      vm.dataLoading = true;
      orchestraTasks.data.then(function() {
        timeEntries.data.then(function() {
          vm.dataLoading = false;

          vm.minDate = timeEntries.minDate;
          vm.maxDate = timeEntries.maxDate;
          $scope.$watch(function() {
            return [vm.minDate, vm.maxDate];
          }, function(newVal, oldVal) {
            if (!angular.equals(newVal, oldVal)) {
              timeEntries.updateEntries(newVal[0], newVal[1]);
            }
          }, true);

          timeEntries.entries.forEach(function(entry) {
            entry.editData = vm.initialEditData(entry);
          });
        });
      });

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

      vm.dayName = function(dateString) {
        if (dateString) {
          return moment(dateString).format('dddd');
        }
      };

      vm.addEntry = function(date) {
        vm.timeEntries.createEntry(date).then(function(entry) {
          vm.editEntry(entry);
        });
      };

      vm.editEntry = function(entry) {
        if (!entry.editing) {
          entry.editData = vm.initialEditData(entry);
          entry.editing = true;
        }
      };

      vm.saveChanges = function(entry) {
        if (vm.entryUnchanged(entry)) {
          vm.cancelChanges();
          return;
        }
        entry.description = entry.editData.description;

        // Only truncate seconds worked if the user has changed things
        if (!angular.equals(entry.editData.timeWorked, entry.time_worked.componentize())) {
          entry.time_worked = moment.duration(entry.editData.timeWorked);
        }

        if (!entry.editData.date.isSame(entry.date)) {
          timeEntries.moveToDate(entry, entry.editData.date);
        }

        entry.assignment = null;
        if (entry.editData.task) {
          entry.assignment = entry.editData.task.assignment_id;
        }
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
          date: entry.date,
          task: orchestraTasks.tasksByAssignmentId[entry.assignment]
        };
        return data;
      };

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
