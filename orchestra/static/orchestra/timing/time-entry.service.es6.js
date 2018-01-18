/* global angular */

import moment from 'moment-timezone'

/**
 * Provides duration stamp for use with Django DurationField.
 */
moment.duration.fn.stamp = function (units) {
  var duration = this

  units = units || ['hours', 'minutes', 'seconds']
  var stamp = ''
  units.forEach(function (unit, i) {
    var unitTime = duration.get(unit)
    stamp += unitTime < 10 ? '0' + unitTime : unitTime
    if (i < units.length - 1) {
      stamp += ':'
    }
  })
  return stamp
}

/**
 * Componentizes a duration by the given units.
 */
moment.duration.fn.componentize = function (units) {
  var duration = this

  units = units || ['h', 'm']

  var components = {}
  units.forEach(function (unit) {
    components[unit] = duration.get(unit)
  })
  return components
}

/**
 * Rounds the duration to the next minute without affecting original data.
 */
moment.duration.fn.roundMinute = function () {
  var duration = this
  return moment.duration({
    h: duration.get('h'),
    m: duration.get('s') ? duration.get('m') + 1 : duration.get('m')
  })
}

/**
 * Rounds up the units provided and returns a human-readable duration.
 */
moment.duration.fn.humanizeUnits = function (units) {
  var duration = this

  var components = duration.componentize(units)
  var durationString = ''
  for (var unit in components) {
    durationString += components[unit] + unit + ' '
  }

  return durationString
}

/**
 * Check whether the time is a certain range before the current time
 */
moment.isBeforeNowBy = function (datetimeString, n = 0, units = 'days') {
  if (!datetimeString) {
    return false
  }
  return moment.utc(datetimeString).tz(moment.tz.guess()).isSameOrBefore(moment().add(n, units))
}

/**
 * Represents a discrete unit of a worker's work time.
 */
export default function TimeEntry ($http) {
  var TimeEntry = function (data) {
    this.initWithData(data)
  }

  /**
   * Endpoint for updating and deleting this time entry.
   */
  TimeEntry.prototype.apiUrl = function () {
    return '/orchestra/api/interface/time_entries/' + this.id + '/'
  }

  /**
   * Initializes a new TimeEntry from the provided data.
   */
  TimeEntry.prototype.initWithData = function (data) {
    var entry = this

    // Copy data and convert datetimes to moments for easy manipulation
    var datetimeFields = ['timer_start_time', 'timer_stop_time']
    for (var field in data) {
      entry[field] = data[field]
      if (datetimeFields.indexOf(field) >= 0 && entry[field]) {
        entry[field] = moment(data[field])
      }
    }
    entry.date = moment(entry.date).startOf('day')
    entry.assignment = data.assignment || undefined

    // Convert time worked to a moment duration
    this.time_worked = moment.duration(data.time_worked)
  }

  /**
   * Deletes the given TimeEntry from the server.
   */
  TimeEntry.prototype.delete = function () {
    $http.delete(this.apiUrl())
    .catch(function () {
      window.alert('Could not delete entry.')
    })
  }

  /**
   * Updates TimeEntry data on the server.
   */
  TimeEntry.prototype.save = function () {
    var entry = this

    var data = angular.copy(entry)

    // Convert datetimes to moments for easy manipulation
    var datetimeFields = ['timer_start_time', 'timer_stop_time']
    datetimeFields.forEach(function (field) {
      if (data[field]) {
        data[field] = data[field].toISOString()
      }
    })

    // Date and time worked need special serialization formats
    data.date = data.date.format('YYYY-MM-DD')
    data.time_worked = data.time_worked.stamp()

    $http.put(this.apiUrl(), data)
      .catch(function () {
        window.alert('Could not update time entry.')
      })
  }

  /**
   * Determines whether the entry is incomplete.
   */
  TimeEntry.prototype.isIncomplete = function () {
    return !(this.description &&
             (this.assignment || this.assignment === 0))
  }

  return TimeEntry
}
