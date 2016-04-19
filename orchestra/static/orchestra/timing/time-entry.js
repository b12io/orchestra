(function() {
  'use strict';

  /**
   * Provides duration stamp for use with Django DurationField.
   */
  moment.duration.fn.stamp = function(units) {
    var duration = this;

    units = units || ['hours', 'minutes', 'seconds'];
    var stamp = '';
    units.forEach(function(unit, i) {
      var unitTime = duration.get(unit);
      stamp += unitTime < 10 ? '0' + unitTime : unitTime;
      if (i < units.length - 1) {
        stamp += ':';
      }
    });
    return stamp;
  };

  /**
   * Componentizes a duration by the given units.
   */
  moment.duration.fn.componentize = function(units) {
    var duration = this;

    units = units || ['hours', 'minutes', 'seconds'];
    var components = {};
    units.forEach(function(unit) {
      components[unit] = duration.get(unit);
    });
    return components;
  };

  /**
   * Represents a discrete unit of a worker's work time.
   */
  angular.module('orchestra.timing')
    .factory('TimeEntry', function($http) {
      var TimeEntry = function(data) {
        if (data.create === true) {
          this.create(data.date);
        }
        else {
          this.initWithData(data);
        }
      };

      /**
       * Endpoint for updating and deleting this time entry.
       */
      TimeEntry.prototype.apiUrl = function() {
        return '/orchestra/api/interface/time_entries/' + this.id + '/';
      };

      /**
       * Initializes a new TimeEntry from the provided data.
       */
      TimeEntry.prototype.initWithData = function(data) {
        var entry = this;

        // Copy data and convert datetimes to moments for easy manipulation
        var datetimeFields = ['timer_start_time', 'timer_stop_time'];
        for (var field in data) {
          entry[field] = data[field];
          if (datetimeFields.indexOf(field) >= 0 && entry[field]) {
            entry[field] = moment(data[field]);
          }
        }
        entry.date = moment(entry.date).startOf('day');

        // Convert time worked to a moment duration and provide editable copy
        this.time_worked = moment.duration(data.time_worked);
        this.time_worked_edit = this.time_worked.componentize();
      };

      /**
       * Creates a new TimeEntry server-side and initializes with returned data.
       */
      TimeEntry.prototype.create = function(date) {
        var entry = this;

        var createUrl = '/orchestra/api/interface/time_entries/';
        this.date = date || moment();
        $http.post(createUrl, {
          date: date.format('YYYY-MM-DD'),
          time_worked: moment.duration().stamp(),

          // Add fake timer start time to keep ordered correctly
          timer_start_time: moment().toISOString()
        })
        .then(function(response) {
          entry.initWithData(response.data);
          entry.editing = true;
        }, function(entry) {
          alert('Could not add new time entry.');
        });
      };

      /**
       * Deletes the given TimeEntry from the server.
       */
      TimeEntry.prototype.delete = function() {
        $http.delete(this.apiUrl())
        .catch(function() {
          alert('Could not delete entry.');
        });
      };

      /**
       * Updates TimeEntry data on the server.
       */
      TimeEntry.prototype.save = function() {
        var entry = this;

        var data = angular.copy(entry);

        // Convert datetimes to moments for easy manipulation
        var datetimeFields = ['timer_start_time', 'timer_stop_time'];
        datetimeFields.forEach(function(field) {
          if (data[field]) {
            data[field] = data[field].toISOString();
          }
        });

        // Date and time worked need special serialization formats
        data.date = data.date.format('YYYY-MM-DD');
        data.time_worked = data.time_worked.stamp();

        $http.put(this.apiUrl(), data)
          .catch(function() {
            alert('Could not update time entry.');
          });
      };

      /**
       * Helpers to update specific TimeEntry fields.
       */
      TimeEntry.prototype.updateDate = function(newDate) {
        this.date = newDate;
        this.editing = false;
        this.save();
      };
      TimeEntry.prototype.updateDuration = function(components) {
        if (!angular.equals(components, this.time_worked.componentize())) {
          this.time_worked = moment.duration(components);
        }
        this.save();
      };

      return TimeEntry;
    });
})();
