(function() {
  // 'use strict';

  angular.module('orchestra.timecard')
    .factory('timecardService', function($http) {
      // var timecardService = {
      timecardService = {
        entries: [],
        entriesByDate: {},
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
          // Don't alter original data
          var data = angular.copy(entryData);

          // Convert datetimes to moments for easy manipulation
          data.time_worked = moment.duration(data.time_worked);

          data.time_worked_edit = {};
          var units = ['hours', 'minutes', 'seconds'];
          units.forEach(function(unit) {
            data.time_worked_edit[unit] = data.time_worked.get(unit);
          });

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
        addEntry: function(entryData) {
          var service = this;
          var convertedData = service.convertEntry(entryData);
          if (!convertedData.date) {
            console.error('Time entry without a date specified:', entry);
            return;
          }
          var dateKey = convertedData.date.toISOString();
          if (!service.entriesByDate[dateKey]) {
            service.entriesByDate[dateKey] = [];
          }
          service.entries.push(convertedData);
          service.entriesByDate[dateKey].push(convertedData);
        },
        createEntry: function() {
          var timeEntryUrl = '/orchestra/api/interface/time_entries/';
          var service = this;
          $http.post(timeEntryUrl, {
            date: moment().format('YYYY-MM-DD'),
            // time_worked: service.durationStamp(moment.duration()),
            time_worked: service.durationStamp(moment.duration({minutes: Math.random() * 10})),

            // Add fake timer start time to keep list ordered
            timer_start_time: moment().toISOString()
          })
          .then(function(response) {
            service.addEntry(response.data);
          }, function() {
            alert('Could not add new time entry.');
          });
        },
        updateEntry: function(entryData) {
          var data = angular.copy(entryData);

          var service = this;
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
          if (confirm('Are you sure you want to delete this entry?')) {
            var service = this;
            var index = service.data.indexOf(entry);
            service.data.splice(index, 1);
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
        return function (obj, addKey) {
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
