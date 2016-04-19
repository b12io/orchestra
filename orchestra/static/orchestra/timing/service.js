(function() {
  'use strict';

  angular.module('orchestra.timing')
    .factory('timingService', function($http, TimeEntry) {
      /**
       * Manage time tracking data for an Orchestra user.
       */
      var timingService = {
        apiUrl: '/orchestra/api/interface/time_entries/',
        entries: [],

        /**
         * Get worker time entries for the provided date range (inclusive).
         */
        getEntriesForDates: function(minDate, maxDate) {
          var service = this;

          // Remove time component from dates
          minDate = minDate.startOf('day');
          maxDate = maxDate.startOf('day');

          $http.get(service.apiUrl, {
            params: {
              min_date: minDate.format('YYYY-MM-DD'),
              max_date: maxDate.format('YYYY-MM-DD'),
            }
          })
          .then(function(response) {
            // Initialize dates in range
            var numDays = maxDate.diff(minDate, 'days');
            service.entriesByDate = {};
            for (var i = 0; i < numDays + 1; i++) {
              var date = minDate.clone().add(i, 'days');
              service.entriesByDate[service.keyForDate(date)] = [];
            }

            // Add newly filtered entries
            response.data.forEach(function(entryData) {
              service.addEntry(entryData);
            });
          }, function() {
            alert('Could not retrieve time entries');
          });
        },

        /**
         * Calculate the total work time for a given date.
         */
        timeWorkedForDate: function(date) {
          var entries = this.entriesByDate[this.keyForDate(date)];
          var totalDuration = moment.duration();
          entries.forEach(function(entry) {
            totalDuration.add(entry.time_worked);
          });
          return totalDuration;
        },

        /**
         * Helpers for adding and deleting time entries.
         */
        createEntry: function(date) {
          return this.addEntry({
            create: true,
            date: date,
          });
        },
        addEntry: function(data) {
          var entry = new TimeEntry(data);
          this.entries.push(entry);
          this.addEntryToDate(entry, entry.date);
          return entry;
        },
        deleteEntry: function(entry) {
          if (confirm('Are you sure you want to delete this entry?')) {
            entry.delete();
            this.removeEntryFromDate(entry, entry.date);
            this.entries.splice(this.entries.indexOf(entry), 1);
          }
        },

        /**
         * Helpers for organizing time entry data by date.
         */
        keyForDate: function(date) {
          if (!moment.isMoment(date)) {
            date = moment(date);
          }
          return date.startOf('day').toISOString();
        },
        addEntryToDate: function(entry, date) {
          var dateISO = this.keyForDate(date);
          this.entriesByDate[dateISO].push(entry);
        },
        removeEntryFromDate: function(entry, date) {
          var dateISO = this.keyForDate(date);
          var index = this.entriesByDate[dateISO].indexOf(entry);
          this.entriesByDate[dateISO].splice(index, 1);
        },
        moveToDate: function(entry, newDate) {
          this.removeEntryFromDate(entry, entry.date);
          this.addEntryToDate(entry, newDate);
          entry.updateDate(newDate);
        },
      };

      // Default filtered view is the past week of time entries
      var maxDate = moment().startOf('day');
      var minDate = maxDate.clone().subtract(7, 'days');
      timingService.getEntriesForDates(minDate, maxDate);
      return timingService;
    });
})();
