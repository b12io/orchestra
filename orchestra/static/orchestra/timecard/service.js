(function() {
  // 'use strict';

  angular.module('orchestra.timecard')
    .factory('timecardService', function($http) {
      // var timecardService = {
      timecardService = {
        entries: [],
        entriesByDate: {},
        addEntryForDate: function(entry, date) {
          var service = this;

          var dateISO = date.toISOString();
          if (service.entriesByDate[dateISO] === undefined) {
            service.entriesByDate[dateISO] = [];
          }
          service.entriesByDate[dateISO].push(entry);
        },
        removeEntryForDate: function(entry, date) {
          var service = this;

          var dateISO = date.toISOString();
          var index = service.entriesByDate[dateISO].indexOf(entry);
          service.entriesByDate[dateISO].splice(index, 1);
          if (!service.entriesByDate[dateISO].length) {
            delete service.entriesByDate[dateISO];
          }
        },
        getDateSum: function(date) {
          if (moment.isMoment(date)) {
            date = date.toISOString();
          }
          var service = this;
          var entries = service.entriesByDate[date];
          var totalDuration = moment.duration();
          entries.forEach(function(entry) {
            totalDuration.add(entry.time_worked);
          });
          return service.humanizeDuration(totalDuration);
        },
        convertEntry: function(entryData) {
          var service = this;

          // Don't alter original data
          var data = angular.copy(entryData);

          // Convert datetimes to moments for easy manipulation
          data.time_worked = moment.duration(data.time_worked);
          data.time_worked_edit = service.timeByUnits(data.time_worked);

          if (data.date) {
            data.date = moment(data.date);
          }
          if (data.timer_start_time) {
            data.timer_start_time = moment(data.timer_start_time);
          }
          if (data.timer_stop_time) {
            data.timer_stop_time = moment(data.timer_stop_time);
          }
          return data;
        },
        timeByUnits: function(duration) {
          var units = ['hours', 'minutes'];
          var unitized = {};
          units.forEach(function(unit) {
            unitized[unit] = duration.get(unit);
          });
          return unitized;
        },
        addEntry: function(entryData) {
          var service = this;

          var entry = service.convertEntry(entryData);
          if (!entry.date) {
            console.error('Time entry without a date specified:', entry);
            return;
          }
          service.entries.push(entry);
          service.addEntryForDate(entry, entry.date);

          return entry;
        },
        createEntry: function(date) {
          var timeEntryUrl = '/orchestra/api/interface/time_entries/';
          var service = this;
          date = date || moment();
          $http.post(timeEntryUrl, {
            date: date.format('YYYY-MM-DD'),
            // time_worked: service.durationStamp(moment.duration()),
            time_worked: service.durationStamp(moment.duration()),

            // Add fake timer start time to keep list ordered
            timer_start_time: moment().toISOString()
          })
          .then(function(response) {
            var entry = service.addEntry(response.data);
            entry.editing = true;
          }, function() {
            alert('Could not add new time entry.');
          });
        },
        updateDate: function(entry, newDate) {
          var service = this;

          service.removeEntryForDate(entry, entry.date);
          service.addEntryForDate(entry, newDate);
          entry.date = newDate;
          entry.editing = false;

          service.saveEntry(entry);
        },
        updateDuration: function(entry) {
          var service = this;
          if (!angular.equals(entry.time_worked_edit, service.timeByUnits(entry.time_worked))) {
            entry.time_worked = moment.duration(entry.time_worked_edit);
          }
          service.saveEntry(entry);
        },
        saveEntry: function(entry) {
          var service = this;

          var data = angular.copy(entry);

          if (data.date) {
            data.date = data.date.format('YYYY-MM-DD');
          }

          if (data.timer_start_time) {
            data.timer_start_time = data.timer_start_time.toISOString();
          }
          if (data.timer_stop_time) {
            data.timer_stop_time = data.timer_stop_time.toISOString();
          }

          var timeEntryUrl = '/orchestra/api/interface/time_entries/' + data.id + '/';
          $http.put(timeEntryUrl, data)
            .then(function(response) {
              console.log(response);
            }, function() {
              alert('Could not update time entry.');
            });
        },
        deleteEntry: function(entry) {
          var service = this;

          var timeEntryUrl = '/orchestra/api/interface/time_entries/' + entry.id + '/';
          if (confirm('Are you sure you want to delete this entry?')) {
            $http.delete(timeEntryUrl)
            .then(function(response) {
              service.removeEntryForDate(entry, entry.date);
              service.entries.splice(service.entries.indexOf(entry), 1);
            }, function() {
              alert('Could not delete entry.');
            });
          }
        },
        getAllEntries: function() {
          var service = this;
          var timeEntryListUrl = '/orchestra/api/interface/time_entries/';
          $http.get(timeEntryListUrl)
          .then(function(response) {
            console.log(response.data);
            response.data.forEach(function(entryData) {
              service.addEntry(entryData);
            });
          }, function() {
            alert('Could not retrieve time entries');
          });
        },
        datetimeFromKey: function(dateEntries) {
          return moment(dateEntries.$key);
        },
        durationStamp: function(duration) {
          if (!duration) {
            duration = moment.duration();
          }
          var units = ['hours', 'minutes', 'seconds'];
          var prettyTime = '';
          units.forEach(function(unit, i) {
            var unitTime = duration.get(unit);
            prettyTime += unitTime < 10 ? '0' + unitTime : unitTime;
            if (i < units.length - 1) {
              prettyTime += ':';
            }
          });
          return prettyTime;
        },
        humanizeDuration: function(duration) {
          if (!duration) {
            duration = moment.duration();
          }
          return duration.get('hours') + 'h ' + duration.get('minutes') + 'm';
        }
      };

      timecardService.getAllEntries();
      return timecardService;
    });

    // Taken from https://github.com/petebacondarwin/angular-toArrayFilter
    angular.module('orchestra.common')
      .filter('toArray', function () {
        return function(obj, addKey) {
          if (!angular.isObject(obj)) return obj;
          if ( addKey === false ) {
            return Object.keys(obj).map(function(key) {
              return obj[key];
            });
          } else {
            return Object.keys(obj).map(function (key) {
              var value = obj[key];
              return angular.isObject(value) ?
                Object.defineProperty(value, '$key', { enumerable: false, value: key}) :
                { $key: key, $value: value };
            });
          }
        };
      });
})();
