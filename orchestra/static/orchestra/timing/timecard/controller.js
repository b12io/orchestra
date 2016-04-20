(function() {
  'use strict';

  angular.module('orchestra.timing')
    .controller('TimecardController', function($routeParams, $scope, timeEntries) {
      var vm = this;
      vm.taskId = $routeParams.taskId;

      vm.timeEntries = timeEntries;

      vm.datetimeFromKey = function(entries) {
        if (entries.$key) {
          return moment(entries.$key);
        }
      };

      vm.humanizeDuration = function(duration) {
        return duration.get('hours') + 'h ' + duration.get('minutes') + 'm';
      };

      vm.prettyDate = function(dateString) {
        // TODO(jrbotros): fix groupby with custom comparator
        if (dateString) {
          return moment(dateString).format('MMMM D');
        }
      };

      vm.editEntry = function(entry) {
        vm.resetEntry(entry);
        entry.editing = !entry.editing;
      };

      vm.saveChanges = function(entry) {
        entry.description = entry.description_edit;
        entry.time_worked = moment.duration(entry.time_worked_edit);
        entry.save();
        entry.editing = false;
        vm.resetEntry(entry);
      };

      vm.cancelChanges = function(entry) {
        entry.editing = false;
        vm.resetEntry(entry);
      };

      vm.resetEntry = function(entry) {
        entry.description_edit = entry.description;
        entry.time_worked_edit = entry.time_worked.componentize();
      };
    });
})();
